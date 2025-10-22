# clarification_agent_claude.py
# Updated Clarification Agent using Claude 3.5 Sonnet (with automatic inference profile lookup)

import boto3, json, re, uuid, os
from datetime import datetime
from strands import Agent

ALLOWED_CATEGORIES = [
    "Scope", "Timeline", "Budget", "Technical", "Compliance",
    "Integration", "Deliverables", "Assumptions", "Other"
]


class ClarificationAgent(Agent):
    def __init__(self, name="clarification-agent-claude", region="us-east-1"):
        super().__init__(name=name)
        self.region = region
        self.s3 = boto3.client("s3", region_name=region)
        self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        self.profile_arn = self._find_inference_profile("anthropic.claude-3-5-sonnet-20241022-v2:0")
        print(f"[INFO] ✅ Using Claude 3.5 Sonnet profile: {self.profile_arn}")

    def _find_inference_profile(self, model_id):
        """Automatically locate an inference profile ARN for Claude."""
        bedrock_mgmt = boto3.client("bedrock", region_name=self.region)
        try:
            profiles = bedrock_mgmt.list_inference_profiles()["inferenceProfileSummaries"]
            for p in profiles:
                if model_id in p.get("modelArn", "") or model_id in p.get("inferenceProfileArn", ""):
                    return p["inferenceProfileArn"]
        except Exception as e:
            print(f"[WARN] Could not list inference profiles: {e}")
        raise Exception(f"No inference profile found for {model_id}")

    # ---------- S3 Utilities ----------
    def read_json_from_s3(self, bucket, key):
        obj = self.s3.get_object(Bucket=bucket, Key=key)
        return json.loads(obj["Body"].read().decode("utf-8"))

    def write_json_to_s3(self, bucket, key, data):
        self.s3.put_object(
            Bucket=bucket, Key=key, Body=json.dumps(data, indent=2).encode("utf-8")
        )
        return f"s3://{bucket}/{key}"

    # ---------- JSON Extraction ----------
    def extract_json(self, text):
        text = re.sub(r"```json|```", "", text).strip()
        m = re.search(r"\{[\s\S]*\}", text)
        return m.group(0) if m else None

    # ---------- Prompt Builder ----------
    def build_prompt(self, parsed):
        domain = parsed.get("domain", "General").lower()
        background = parsed.get("background", "")[:800]
        technical = parsed.get("technical_asks", "")[:600]
        functional = parsed.get("functional_asks", "")[:600]
        timelines = parsed.get("timelines", "not specified")
        budget = parsed.get("estimated_budget", "not specified")

        domain_context = {
            "health": "Healthcare domain — focus on interoperability (HL7/FHIR), HIPAA compliance, and clinical analytics.",
            "finance": "Finance domain — emphasize PCI-DSS, risk/fraud prevention, and regulatory compliance.",
            "retail": "Retail domain — emphasize scalability, omnichannel experiences, and inventory integrations.",
            "manufacturing": "Manufacturing domain — focus on predictive maintenance, IoT data, and automation reliability.",
        }
        domain_hint = next((v for k, v in domain_context.items() if k in domain), 
                           "Domain unclear — focus on scope, integration gaps, and deliverables.")

        return f"""
You are an experienced **Presales Solution Architect** preparing for a client clarification round.

Context:
- Domain: {domain}
- Timeline: {timelines}
- Estimated Budget: {budget}

{domain_hint}

Key RFP Extracts:
Background: {background}
Functional Requirements: {functional}
Technical Requirements: {technical}

Task:
1️⃣ Review the above content.
2️⃣ Identify up to 5 critical clarification questions a presales architect should ask to reduce delivery risk.
3️⃣ Each question must be unique, clear, and specific to this RFP (avoid generic queries).
4️⃣ Include one of these categories: {', '.join(ALLOWED_CATEGORIES)}.
5️⃣ Return **only valid JSON**, no markdown or explanations, using this schema:

{{
  "clarifications": [
    {{
      "question_id": "<uuid4>",
      "category": "<category>",
      "question": "<text ending with ?>",
      "required": true,
      "priority": 1
    }}
  ]
}}
"""

    # ---------- Main Execution ----------
    def run(self, bucket_in, parsed_key, bucket_out):
        print(f"[INFO] Running ClarificationAgent (Claude 3.5) for: {parsed_key}")

        parsed = self.read_json_from_s3(bucket_in, parsed_key)
        prompt = self.build_prompt(parsed)

        model_output = None

        # ---------- Try Claude 3.5 Sonnet ----------
        try:
            print("[INFO] 🚀 Invoking Claude 3.5 Sonnet...")
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
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
            model_output = out["content"][0]["text"]
            print("[INFO] ✅ Claude 3.5 Sonnet succeeded.")
        except Exception as e:
            print(f"[WARN] Claude failed: {e}")
            model_output = None

        # ---------- Titan fallback ----------
        if not model_output:
            try:
                print("[INFO] 🔁 Falling back to Titan Text Express...")
                payload = {
                    "inputText": prompt,
                    "textGenerationConfig": {"temperature": 0.4, "maxTokenCount": 2000},
                }
                resp = self.bedrock.invoke_model(
                    modelId="amazon.titan-text-express-v1",
                    body=json.dumps(payload),
                    accept="application/json",
                    contentType="application/json",
                )
                raw = resp["body"].read().decode("utf-8")
                out = json.loads(raw)
                model_output = out["results"][0]["outputText"]
                print("[INFO] ✅ Titan succeeded as fallback.")
            except Exception as e:
                print(f"[ERROR] Titan fallback also failed: {e}")
                raise

        # ---------- Parse Clarifications ----------
        clarifications = []
        extracted = self.extract_json(model_output)
        if extracted:
            try:
                data = json.loads(extracted)
                clarifications = data.get("clarifications", [])
                print(f"[INFO] Extracted {len(clarifications)} clarifications.")
            except Exception as e:
                print(f"[WARN] JSON parse failed: {e}")

        # ---------- Fallback Generator ----------
        if not clarifications:
            print("[WARN] Using fallback clarification generator.")
            clarifications = [
                {
                    "question_id": str(uuid.uuid4()),
                    "category": "Timeline",
                    "question": f"Can you confirm if the stated project timeline ({parsed.get('timelines','N/A')}) includes testing and support phases?",
                    "required": True,
                    "priority": 1,
                },
                {
                    "question_id": str(uuid.uuid4()),
                    "category": "Budget",
                    "question": f"Does the provided budget ({parsed.get('estimated_budget','N/A')}) include licenses and cloud costs?",
                    "required": True,
                    "priority": 1,
                },
                {
                    "question_id": str(uuid.uuid4()),
                    "category": "Technical",
                    "question": "Do you have preferred cloud or technology stack (e.g., AWS, Azure)?",
                    "required": True,
                    "priority": 1,
                },
            ]

        clarifications_obj = {
            "clarifications": clarifications[:5],
            "status": "pending",
            "source_file": parsed_key,
            "generated_at": datetime.utcnow().isoformat(),
        }

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        user_prefix = parsed_key.split("/")[0]
        out_folder = f"{user_prefix}/clarifications/"
        out_key = f"{out_folder}{os.path.basename(parsed_key).replace('.json','')}_clarifications_{ts}.json"

        self.s3.put_object(Bucket=bucket_out, Key=out_folder)
        s3uri = self.write_json_to_s3(bucket_out, out_key, clarifications_obj)
        print(f"[INFO] Clarifications saved to {s3uri}")
        return out_key


# --- Local test example ---
if __name__ == "__main__":
    agent = ClarificationAgent(region="us-east-1")
    key = "ravi/parsed_outputs/RFP_1_20251013_045445_parsed.json"
    output = agent.run("presales-rfp-outputs", key, "presales-rfp-outputs")
    print("✅ Output JSON:", output)
