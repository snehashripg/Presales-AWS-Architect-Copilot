# rfx_orchestrator_agent.py
"""
RFxOrchestratorAgent — runs the full RFP automation pipeline sequentially
Steps:
1️⃣ Parse RFP document
2️⃣ Generate clarifications
3️⃣ Estimate pricing & funding
4️⃣ Draft Statement of Work (SOW)
5️⃣ (Optional) Generate Architecture Diagram
"""

import os, json, time, traceback
from datetime import datetime

from rfx_parsing_agent import RFxParsingAgent
from clarification_agent import ClarificationAgent
from pricing_funding_agent import PricingFundingAgent
from sow_drafting_agent import SOWDraftingAgent
# from architecture_diagram_agent import ArchitectureDiagramAgent  # optional

import boto3


class RFxOrchestratorAgent:
    def __init__(self, region="us-east-1"):
        self.region = region
        self.s3 = boto3.client("s3", region_name=region)
        self.parser = RFxParsingAgent(region=region)
        self.clarifier = ClarificationAgent(region=region)
        self.pricer = PricingFundingAgent(region=region)
        self.sow = SOWDraftingAgent(region=region)
        # self.diagrammer = ArchitectureDiagramAgent(region=region)

    def run(self, bucket_in, input_key, bucket_out):
        print(f"\n🚀 Starting RFx Orchestrator Agent for: {input_key}")
        start_time = time.time()

        results = {
            "input_file": input_key,
            "steps": [],
            "status": "running",
            "started_at": datetime.utcnow().isoformat()
        }

        user_prefix = input_key.split("/")[0]

        try:
            # 1️⃣ Parsing
            print("\n🧾 [STEP 1] Running RFx Parsing Agent...")
            parsed_key = self.parser.run(bucket_in, input_key, bucket_out)
            results["steps"].append({"step": "RFx Parsing", "output": parsed_key, "status": "success"})

            # 2️⃣ Clarifications
            print("\n💬 [STEP 2] Running Clarification Agent...")
            clar_key = self.clarifier.run(bucket_out, parsed_key, bucket_out)
            results["steps"].append({"step": "Clarification", "output": clar_key, "status": "success"})

            # 3️⃣ Pricing & Funding
            print("\n💰 [STEP 3] Running Pricing & Funding Agent...")
            pricing_key = self.pricer.run(bucket_out, parsed_key, clar_key, bucket_out)
            results["steps"].append({"step": "Pricing & Funding", "output": pricing_key, "status": "success"})

            # 4️⃣ SOW Drafting
            print("\n📄 [STEP 4] Running SOW Drafting Agent...")
            sow_key = self.sow.run(bucket_out, parsed_key, clar_key, pricing_key, bucket_out)
            results["steps"].append({"step": "SOW Drafting", "output": sow_key, "status": "success"})

            # 5️⃣ (Optional) Architecture Diagram
            # print("\n🏗️ [STEP 5] Generating Architecture Diagram...")
            # diagram_key = self.diagrammer.run(bucket_out, parsed_key, clar_key, sow_key, bucket_out)
            # results["steps"].append({"step": "Architecture Diagram", "output": diagram_key, "status": "success"})

            # ✅ Success
            total_time = round(time.time() - start_time, 2)
            results["status"] = "completed"
            results["total_time_seconds"] = total_time
            results["completed_at"] = datetime.utcnow().isoformat()
            print(f"\n✅ Workflow completed successfully in {total_time}s.")

        except Exception as e:
            traceback.print_exc()
            err_msg = str(e)
            results["status"] = "failed"
            results["error"] = err_msg
            print(f"\n❌ Workflow failed: {err_msg}")

        # Save run log to S3
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_key = f"{user_prefix}/workflow_logs/rfx_orchestrator_run_{ts}.json"
        self.s3.put_object(
            Bucket=bucket_out,
            Key=log_key,
            Body=json.dumps(results, indent=2).encode("utf-8"),
        )
        print(f"\n🧾 Log saved to: s3://{bucket_out}/{log_key}")

        return results


# ✅ Example for SageMaker / Notebook Execution
if __name__ == "__main__":
    bucket_in = "presales-rfp-inputs"
    bucket_out = "presales-rfp-outputs"
    input_key = "ravi/RFP_1.pdf"

    orchestrator = RFxOrchestratorAgent(region="us-east-1")
    results = orchestrator.run(bucket_in, input_key, bucket_out)
    print(json.dumps(results, indent=2))
