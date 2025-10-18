# rfx_parsing_agent_hybrid.py
# Smart hybrid version — tries Claude 3.5 Sonnet first, falls back to Titan Express

import boto3, json, os, tempfile, time, re
from datetime import datetime
from strands import Agent
from docx import Document
import fitz  # PyMuPDF


class RFxParsingAgent(Agent):
    def __init__(self, name="rfx-parsing-agent-hybrid", region="us-east-1"):
        super().__init__(name=name)
        self.s3 = boto3.client("s3", region_name=region)
        self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        self.region = region
        self.profile_arn = self._find_inference_profile("anthropic.claude-3-5-sonnet-20241022-v2:0")
        print(f"[INFO] ✅ Using Claude inference profile: {self.profile_arn}")

    # ---------- Utility ----------
    def _find_inference_profile(self, model_id):
        """Find a matching inference profile for a given model."""
        bedrock_mgmt = boto3.client("bedrock", region_name=self.region)
        try:
            profiles = bedrock_mgmt.list_inference_profiles()["inferenceProfileSummaries"]
            for p in profiles:
                if model_id in p.get("modelArn", "") or model_id in p.get("inferenceProfileArn", ""):
                    return p["inferenceProfileArn"]
        except Exception as e:
            print(f"[WARN] Could not list inference profiles: {e}")
        return None

    # ---------- File Readers ----------
    def extract_text_from_pdf(self, bucket, key):
        print("[INFO] Extracting text from PDF using PyMuPDF...")
        tmp_path = tempfile.mktemp(suffix=".pdf")
        self.s3.download_file(bucket, key, tmp_path)
        text_data = ""
        try:
            doc = fitz.open(tmp_path)
            for page in doc:
                text_data += page.get_text()
            doc.close()
        except Exception as e:
            print(f"[WARN] PyMuPDF failed: {e}")
        os.unlink(tmp_path)
        return text_data

    def extract_text_from_docx(self, local_path):
        doc = Document(local_path)
        return "\n".join([p.text for p in doc.paragraphs])

    def read_text_file(self, bucket, key):
        obj = self.s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read().decode("utf-8")

    # ---------- Preprocess ----------
    def preprocess_text(self, text, max_chars=15000):
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        text = text.replace('"', "'").strip()
        if len(text) > max_chars:
            print(f"[INFO] Truncating RFP text from {len(text)} → {max_chars} chars")
            text = text[:max_chars]
        return text

    # ---------- Main Run ----------
    def run(self, bucket_in, input_key, bucket_out):
        print(f"\n{'='*70}")
        print(f"[INFO] Starting Hybrid RFX Parsing Agent for: {input_key}")
        print(f"{'='*70}")

        ext = os.path.splitext(input_key.lower())[1]
        tmp = tempfile.NamedTemporaryFile(delete=False)
        self.s3.download_file(bucket_in, input_key, tmp.name)

        # Load text
        if ext == ".pdf":
            text = self.extract_text_from_pdf(bucket_in, input_key)
        elif ext == ".docx":
            text = self.extract_text_from_docx(tmp.name)
        elif ext == ".txt":
            text = self.read_text_file(bucket_in, input_key)
        else:
            raise ValueError("Unsupported file format (.pdf, .docx, .txt only)")
        tmp.close()
        os.unlink(tmp.name)

        text = self.preprocess_text(text)

        prompt = f"""
You are an expert presales analyst.
Extract the following fields from this RFP and return a VALID JSON only:

- customer_name
- project_title
- domain
- background
- functional_asks
- technical_asks
- timelines
- estimated_budget
- compliance
- deliverables

RFP Text:
{text}
"""

        parsed_json = None

        # ---------- Try Claude First ----------
        try:
            print("[INFO] 🚀 Trying Claude 3.5 Sonnet...")
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.3,
                "messages": [{"role": "user", "content": prompt}],
            }
            resp = self.bedrock.invoke_model(
                modelId=self.profile_arn,
                body=json.dumps(payload),
                accept="application/json",
                contentType="application/json",
            )
            out = json.loads(resp["body"].read().decode("utf-8"))
            parsed_text = out["content"][0]["text"]
            print("[INFO] ✅ Claude succeeded.")
        except Exception as e:
            print(f"[WARN] Claude failed: {e}")
            parsed_text = None

        # ---------- Fallback: Titan ----------
        if not parsed_text:
            print("[INFO] 🔁 Falling back to Titan Text Express...")
            payload = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 2048,
                    "temperature": 0.4,
                    "topP": 1,
                },
            }
            resp = self.bedrock.invoke_model(
                modelId="amazon.titan-text-express-v1",
                body=json.dumps(payload),
                accept="application/json",
                contentType="application/json",
            )
            result = json.loads(resp["body"].read().decode("utf-8"))
            parsed_text = result["results"][0]["outputText"]
            print("[INFO] ✅ Titan fallback succeeded.")

        # ---------- Parse JSON ----------
        match = re.search(r"\{.*\}", parsed_text, re.DOTALL)
        json_str = match.group(0) if match else parsed_text
        try:
            parsed_json = json.loads(json_str)
        except Exception as e:
            print(f"[WARN] JSON parsing issue: {e}")
            parsed_json = {"error": "Invalid JSON", "raw_output": parsed_text[:1000]}

        # ---------- Save ----------
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        user_prefix = input_key.split("/")[0]
        file_base = os.path.basename(input_key).split(".")[0]
        out_key = f"{user_prefix}/parsed_outputs/{file_base}_{ts}_parsed.json"

        self.s3.put_object(
            Bucket=bucket_out,
            Key=out_key,
            Body=json.dumps(parsed_json, indent=2).encode("utf-8"),
        )

        print(f"[INFO] ✅ Saved parsed output to s3://{bucket_out}/{out_key}")
        print(f"{'='*70}")
        return out_key


# --- Local test example ---
if __name__ == "__main__":
    agent = RFxParsingAgent(region="us-east-1")
    result = agent.run(
        bucket_in="presales-rfp-inputs",
        input_key="ravi/RFP_1.pdf",
        bucket_out="presales-rfp-outputs"
    )
    print("✅ Output JSON:", result)
