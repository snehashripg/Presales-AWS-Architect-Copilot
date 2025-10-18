# pricing_funding_agent_claude.py
"""
Pricing & Funding Check Agent (Claude 3.5 Sonnet)
- Reads parsed RFP JSON and clarifications JSON from S3
- Produces estimated cost ranges, feasibility, funding recommendations
- Writes output JSON to S3 under <user>/pricing_outputs/
"""

import boto3
import json
import re
import uuid
import os
from datetime import datetime


# Base Agent fallback for local use
try:
    from strands import Agent
    BaseAgent = Agent
except Exception:
    class BaseAgent:
        def __init__(self, name="pricing-funding-agent"):
            self.name = name


class PricingFundingAgent(BaseAgent):
    def __init__(self, name="pricing-funding-agent", region="us-east-1"):
        super().__init__(name=name)
        self.region = region
        self.s3 = boto3.client("s3", region_name=region)
        self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        self.profile_arn = self._find_inference_profile("anthropic.claude-3-5-sonnet-20241022-v2:0")
        print(f"[INFO] ✅ Using Claude 3.5 Sonnet profile: {self.profile_arn}")

    # ---------- Bedrock Profile Utility ----------
    def _find_inference_profile(self, model_id):
        bedrock_mgmt = boto3.client("bedrock", region_name=self.region)
        try:
            profiles = bedrock_mgmt.list_inference_profiles()["inferenceProfileSummaries"]
            for p in profiles:
                if model_id in p.get("modelArn", "") or model_id in p.get("inferenceProfileArn", ""):
                    return p["inferenceProfileArn"]
        except Exception as e:
            print(f"[WARN] Could not list inference profiles: {e}")
        raise Exception(f"No inference profile found for {model_id}")

    # ---------- S3 Helpers ----------
    def read_json(self, bucket, key):
        obj = self.s3.get_object(Bucket=bucket, Key=key)
        return json.loads(obj["Body"].read().decode("utf-8"))

    def write_json(self, bucket, key, payload):
        self.s3.put_object(
            Bucket=bucket, Key=key, Body=json.dumps(payload, indent=2).encode("utf-8")
        )
        return f"s3://{bucket}/{key}"

    # ---------- Core Numeric Extractors ----------
    def extract_numeric_assumptions(self, parsed):
        text_blob = json.dumps(parsed).lower()

        def extract_int(pattern, default):
            m = re.search(pattern, text_blob)
            return int(m.group(1)) if m else default

        num_apps = extract_int(r'(\b\d{1,4})\s*(?:apps|applications|services)\b', 50)
        data_tb = extract_int(r'(\b\d{1,4})\s*(?:tb|terabytes|tb of data)\b', 20)
        months = extract_int(r'(\b\d{1,3})\s*(?:month|months)\b', 12)

        # Extract explicit budget if mentioned
        budget_match = re.search(r'\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)\s*(?:m|million)?', text_blob)
        budget_val = None
        if budget_match:
            num = budget_match.group(1).replace(",", "")
            if re.search(r'(m|million)', text_blob):
                budget_val = float(num) * 1_000_000
            else:
                budget_val = float(num)

        return {
            "num_apps": num_apps,
            "data_tb": data_tb,
            "duration_months": months,
            "explicit_budget": budget_val,
        }

    def simple_cost_model(self, assumptions):
        n_apps = assumptions["num_apps"]
        tb = assumptions["data_tb"]
        months = assumptions["duration_months"]

        infra_per_tb_month = 200.0
        infra_monthly = tb * infra_per_tb_month
        migration_per_app = 10000.0
        migration_cost = n_apps * migration_per_app
        data_migration_per_tb = 5000.0
        data_mig_cost = tb * data_migration_per_tb
        pm_and_testing = 0.15 * (migration_cost + data_mig_cost)
        contingency = 0.20 * (migration_cost + data_mig_cost + pm_and_testing)
        base_total = migration_cost + data_mig_cost + pm_and_testing + contingency + infra_monthly * months

        return {
            "low": round(base_total * 0.9, 2),
            "high": round(base_total * 1.25, 2),
            "currency": "USD",
            "breakdown": {
                "infra_monthly": infra_monthly,
                "migration_per_app_total": migration_cost,
                "data_migration_total": data_mig_cost,
                "pm_and_testing": pm_and_testing,
                "contingency": contingency,
                "duration_months": months,
            },
        }

    def evaluate_feasibility(self, est_range, explicit_budget):
        low = est_range["low"]
        high = est_range["high"]
        if explicit_budget:
            if explicit_budget >= high:
                status = "Feasible"
                gap_abs = 0
                gap_pct = 0
            elif explicit_budget >= low:
                status = "Tight"
                gap_abs = high - explicit_budget
                gap_pct = (gap_abs / high) * 100
            else:
                status = "Unrealistic"
                gap_abs = high - explicit_budget
                gap_pct = (gap_abs / high) * 100
            return {
                "feasibility": status,
                "funding_gap_absolute": round(gap_abs, 2),
                "funding_gap_pct": round(gap_pct, 2),
            }
        avg = (low + high) / 2
        if avg < 500_000:
            return {"feasibility": "Feasible", "funding_gap_absolute": None, "funding_gap_pct": None}
        elif avg < 2_000_000:
            return {"feasibility": "Feasible with caution", "funding_gap_absolute": None, "funding_gap_pct": None}
        else:
            return {"feasibility": "Needs detailed scoping", "funding_gap_absolute": None, "funding_gap_pct": None}

    # ---------- Claude 3.5 Summary ----------
    def call_bedrock_summary(self, context):
        prompt = f"""
You are a **Senior Cloud Presales Architect**.
Based on this RFP context (parsed + clarifications + assumptions), provide a 3-5 sentence summary:
1️⃣ Comment on the estimated cost reasonableness and feasibility.
2️⃣ Mention top 2 delivery or cost risks.
3️⃣ Recommend 1 funding path (POC / Pilot / Full Funding).
Return only plain text.

Context:
{json.dumps(context, indent=2)[:12000]}
"""
        # Try Claude 3.5 Sonnet
        try:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 800,
                "temperature": 0.4,
                "messages": [{"role": "user", "content": prompt}],
            }

            resp = self.bedrock.invoke_model(
                modelId=self.profile_arn,
                body=json.dumps(payload),
                accept="application/json",
                contentType="application/json",
            )
            out = json.loads(resp["body"].read().decode("utf-8"))
            if "content" in out:
                return out["content"][0]["text"].strip()
        except Exception as e:
            print(f"[WARN] Claude 3.5 failed: {e}")

        # Titan fallback
        try:
            payload = {
                "inputText": prompt,
                "textGenerationConfig": {"temperature": 0.4, "maxTokenCount": 800},
            }
            resp = self.bedrock.invoke_model(
                modelId="amazon.titan-text-express-v1",
                body=json.dumps(payload),
                accept="application/json",
                contentType="application/json",
            )
            out = json.loads(resp["body"].read().decode("utf-8"))
            if "results" in out:
                return out["results"][0]["outputText"].strip()
        except Exception as e:
            print(f"[WARN] Titan fallback failed: {e}")

        return "Unable to generate LLM summary due to model access issues."

    # ---------- Main Run ----------
    def run(self, bucket_in, parsed_key, clarification_key, bucket_out):
        print(f"[INFO] PricingFundingAgent (Claude 3.5) run for: parsed={parsed_key}, clarifications={clarification_key}")

        parsed = self.read_json(bucket_in, parsed_key)
        clarifications = None
        if clarification_key:
            try:
                clarifications = self.read_json(bucket_in, clarification_key)
            except Exception as e:
                print(f"[WARN] Could not read clarifications: {e}")

        assumptions = self.extract_numeric_assumptions(parsed)
        cost_est = self.simple_cost_model(assumptions)
        explicit_budget = assumptions.get("explicit_budget") or parsed.get("estimated_budget")
        feasibility = self.evaluate_feasibility(cost_est, explicit_budget)

        combined_context = {
            "parsed": parsed,
            "clarifications": clarifications,
            "assumptions": assumptions,
            "cost_estimate": cost_est,
            "feasibility": feasibility,
        }
        llm_summary = self.call_bedrock_summary(combined_context)

        total_high = cost_est["high"]
        recs = []
        if total_high <= 100000:
            recs.append({"type": "Small POC", "amount": min(50000, round(total_high*0.2)), "rationale": "Validate approach quickly"})
        elif total_high <= 500000:
            recs.append({"type": "POC + Pilot", "amount": round(total_high*0.15), "rationale": "Proof-of-value then expand"})
        else:
            recs.append({"type": "POC", "amount": round(total_high*0.05), "rationale": "Validate cost assumptions"})
            recs.append({"type": "Initial Delivery", "amount": round(total_high*0.25), "rationale": "Fund first delivery tranche"})

        output = {
            "pricing_check": {
                "estimated_cost_range": {
                    "low": cost_est["low"],
                    "high": cost_est["high"],
                    "currency": cost_est["currency"],
                },
                "breakdown": cost_est["breakdown"],
                "feasibility": feasibility,
                "funding_recommendations": recs,
                "llm_summary": llm_summary,
            },
            "source_files": {"parsed": parsed_key, "clarifications": clarification_key},
            "generated_at": datetime.utcnow().isoformat(),
            "report_id": str(uuid.uuid4()),
        }

        user_prefix = parsed_key.split("/")[0]
        out_folder = f"{user_prefix}/pricing_outputs/"
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_key = f"{out_folder}{os.path.basename(parsed_key).replace('.json','')}_pricing_{ts}.json"

        try:
            self.s3.put_object(Bucket=bucket_out, Key=out_folder)
        except Exception:
            pass

        s3uri = self.write_json(bucket_out, out_key, output)
        print(f"[INFO] ✅ Pricing report saved to {s3uri}")
        return out_key


# --- Local test example ---
if __name__ == "__main__":
    agent = PricingFundingAgent(region="us-east-1")
    out = agent.run(
        bucket_in="presales-rfp-outputs",
        parsed_key="ravi/parsed_outputs/RFP_1_20251013_045445_parsed.json",
        clarification_key="ravi/clarifications/RFP_1_20251013_045445_parsed_clarifications_20251013_045454.json",
        bucket_out="presales-rfp-outputs"
    )
    print("✅ Output:", out)
