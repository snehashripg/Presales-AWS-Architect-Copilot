import json
import boto3
from botocore.config import Config

# Initialize outside handler (recommended for Lambda cold start optimization)
my_config = Config(
    region_name="us-east-1",
    connect_timeout=60,
    read_timeout=300
)
client = boto3.client('bedrock-agentcore', region_name='us-east-1', config=my_config)

AGENT_RUNTIME_ARN = 'arn:aws:bedrock-agentcore:us-east-1:040504913362:runtime/solution_architect_copilot_agentcore-QfX1ZG3kA6'

def lambda_handler(event, context):
    """
    Lambda entrypoint for invoking a Bedrock AgentCore runtime.
    
    Expected event (from frontend / API Gateway):
    {
        "invocation_type": "streaming" | "standard",
        "prompt": "Process RFP",
        "bucket": "presales-rfp-inputs",
        "s3_key": "snehashri.pg/RFP_1.pdf",
        "action": "full_pipeline"
    }
    """
    print("Received event:", json.dumps(event))

    # Default values if not provided
    invocation_type = event.get("invocation_type", "streaming")
    runtime_session_id = event.get(
        "runtimeSessionId",
        "session_" + ("x" * 33)  # Ensure min 33 chars
    )

    payload = json.dumps(event)

    # Call Bedrock Agent Runtime
    response = client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_RUNTIME_ARN,
        runtimeSessionId=runtime_session_id,
        payload=payload,
        qualifier="DEFAULT"
    )

    result_content = []

    # --- STREAMING RESPONSE ---
    if "text/event-stream" in response.get("contentType", ""):
        buffer = ""
        for chunk in response["response"].iter_lines(chunk_size=150):
            if chunk:
                chunk = chunk.decode("utf-8")
                buffer += chunk
                if "data: " in buffer:
                    parts = buffer.split("data: ")
                    for part in parts[1:]:
                        text = part.strip()
                        if text:
                            print(text)
                            result_content.append(text)
                    buffer = parts[-1]
    else:
        # --- NON-STREAMING RESPONSE ---
        response_body = response['response'].read()
        response_data = json.loads(response_body)
        result_content.append(response_data)
        print("Agent Response:", json.dumps(response_data, indent=2))

    print("\n=== Complete Collected Output ===")
    print(json.dumps(result_content, indent=2))

    # --- Return formatted API response ---
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "result": result_content
        })
    }
