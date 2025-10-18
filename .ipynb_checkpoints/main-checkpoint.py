# # ============================================
# # Local Testing
# # ============================================

# if __name__ == "__main__":
#     """
#     For local testing with Strands CLI:
    
#     1. Install: pip install strands
#     2. Run: python main.py
#     3. Test: strands test main.py
#     """
    
#     # Option 1: Run with Strands development server
#     app.run()
    
#     # Option 2: Test locally with mock event
#     # import json

#     # # Simulate a Lambda event
#     # event = {
#     #     "invocation_type": "streaming",  # or "synchronous" if you want non-streaming
#     #     "prompt": "Please process the RFx document at s3://presales-rfp-inputs/test/RFP_5.pdf.",
#     #     "bucket": "presales-rfp-inputs",
#     #     "s3_key": "test/RFP_5.pdf",
#     #     "action": "full_pipeline"
#     # }

#     # print("🔹 Running Lambda simulation locally...\n")

#     # # You don't need a real context object for local testing
#     # response = lambda_handler(event, None)

#     # print("\n\n🔹 Lambda Response:\n")
#    # print(json.dumps(response, indent=2))

#!/usr/bin/env python3
"""
main.py - RFx Multi-Agent System with Strands AgentCore Runtime
Deploy to AWS Lambda with streaming support and Bedrock Agent Runtime
"""

from strands import Agent, tool
from strands.models import BedrockModel
from strands.agent.conversation_manager import SummarizingConversationManager
from bedrock_agentcore import BedrockAgentCoreApp
import boto3
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Initialize S3 client
s3_client = boto3.client('s3')

# Initialize AgentCore app
app = BedrockAgentCoreApp()

# ============================================
# Agent Tool Definitions
# ============================================

@tool
def rfx_parsing_tool(bucket: str, s3_key: str) -> Dict[str, Any]:
    """
    Parse RFx documents (RFP/RFQ/RFI) and extract structured information.
    
    Args:
        bucket: S3 bucket containing the RFx document
        s3_key: S3 key/path to the RFx document
    
    Returns:
        Parsed RFx data including requirements, deadlines, and specifications
    """
    try:
        from rfx_parsing_agent import RFxParsingAgent
        
        parser = RFxParsingAgent()
        output_bucket = bucket.replace('-inputs', '-outputs')
        
        print(f"[TOOL] Parsing document s3://{bucket}/{s3_key}")
        result_key = parser.run(bucket, s3_key, output_bucket)
        
        # Read parsed result
        response = s3_client.get_object(Bucket=output_bucket, Key=result_key)
        parsed_data = json.loads(response['Body'].read())
        
        return {
            'status': 'success',
            'output_key': result_key,
            'bucket': output_bucket,
            'parsed_data': parsed_data,
            'message': f'Successfully parsed document. Output saved to: {result_key}'
        }
    except Exception as e:
        print(f"[ERROR] Parsing tool failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'message': f'Failed to parse document: {str(e)}'
        }


@tool
def clarification_tool(bucket: str, parsed_key: str) -> Dict[str, Any]:
    """
    Generate clarification questions for ambiguous RFx requirements.
    
    Args:
        bucket: S3 bucket containing parsed data
        parsed_key: S3 key to parsed RFx data
    
    Returns:
        List of clarification questions organized by category
    """
    try:
        from clarification_agent import ClarificationAgent
        
        agent = ClarificationAgent()
        
        # Ensure output bucket
        bucket_out = bucket.replace('-inputs', '-outputs') if bucket.endswith('-inputs') else bucket
        
        print(f"[TOOL] Generating clarifications from s3://{bucket}/{parsed_key}")
        result_key = agent.run(bucket, parsed_key, bucket_out)
        
        # Read clarifications
        response = s3_client.get_object(Bucket=bucket_out, Key=result_key)
        clarifications = json.loads(response['Body'].read())
        
        return {
            'status': 'success',
            'output_key': result_key,
            'bucket': bucket_out,
            'clarifications': clarifications,
            'message': f'Generated {len(clarifications.get("clarifications", []))} clarification questions. Output saved to: {result_key}'
        }
    except Exception as e:
        print(f"[ERROR] Clarification tool failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'message': f'Failed to generate clarifications: {str(e)}'
        }


# ============================================
# ADD THIS NEW TOOL DEFINITION (after existing tools)
# ============================================

@tool
def aws_architecture_generation_tool(
    parsed_s3_key: str,
    clarification_s3_key: str,
    bucket: str = "presales-rfp-outputs"
) -> Dict[str, Any]:
    """
    Generate AWS reference architecture based on parsed RFx and clarifications.
    
    Searches both Knowledge Base (approved architectures) and MCP Server (AWS references).
    Selects best template and generates custom architecture.
    
    Args:
        parsed_s3_key: S3 key to parsed RFx JSON (from parsing agent)
        clarification_s3_key: S3 key to clarifications JSON (from clarification agent)
        bucket: S3 bucket containing the data
    
    Returns:
        Architecture generation result with S3 path to saved diagram
    """
    try:
        from aws_architecture_agent import AWSArchitectureAgent
        print(f"[AWS-ARCH-TOOL] 🏗️ Generating AWS architecture...")
        print(f"[AWS-ARCH-TOOL]   Parsed: {parsed_s3_key}")
        print(f"[AWS-ARCH-TOOL]   Clarifications: {clarification_s3_key}")
        
        # Read parsed RFx data
        print(f"[AWS-ARCH-TOOL] 📖 Reading parsed RFx data...")
        parsed_response = s3_client.get_object(Bucket=bucket, Key=parsed_s3_key)
        parsed_data = json.loads(parsed_response['Body'].read())
        
        # Read clarifications
        print(f"[AWS-ARCH-TOOL] 📖 Reading clarifications...")
        clar_response = s3_client.get_object(Bucket=bucket, Key=clarification_s3_key)
        clarifications = json.loads(clar_response['Body'].read())
        
        # Extract technical requirements
        # Match the actual fields from RFxParsingAgent output
        technical_requirements = f"""
Technical Requirements from RFx:

**Customer:** {parsed_data.get('customer_name', 'Not specified')}
**Project Title:** {parsed_data.get('project_title', 'Not specified')}

**Domain:** {parsed_data.get('domain', 'General')}

**Background:**
{parsed_data.get('background', 'Not specified')}

**Functional Requirements:**
{parsed_data.get('functional_asks', 'Not specified')}

**Technical Requirements:**
{parsed_data.get('technical_asks', 'Not specified')}

**Deliverables:**
{parsed_data.get('deliverables', 'Not specified')}

**Compliance Requirements:**
{parsed_data.get('compliance', 'Not specified')}

**Timeline:**
{parsed_data.get('timelines', 'Not specified')}

**Estimated Budget:**
{parsed_data.get('estimated_budget', 'Not specified')}

**Key Clarifications from Client:**
{json.dumps(clarifications.get('clarifications', [])[:5], indent=2) if clarifications.get('clarifications') else 'No clarifications generated yet'}
"""
        
        print(f"[AWS-ARCH-TOOL] 🤖 Initializing architecture agent...")
        
        
        agent = AWSArchitectureAgent()
        # CRITICAL: Everything must happen INSIDE the MCP context
        if agent.aws_docs_client and agent.aws_diag_client:
            print("[INFO] Starting MCP client sessions...")
            with agent.aws_docs_client, agent.aws_diag_client:
                print("[INFO] MCP clients started, creating agent...")
                agent.create_agent()  # Create agent INSIDE context - this calls list_tools_sync()
                
                print("[INFO] Running architecture generation...")
                result = agent.run(
                    technical_requirements=technical_requirements,
                    parsed_key=parsed_s3_key,
                    output_bucket="presales-rfp-outputs"
                )
    

        # Extract user prefix from parsed key (e.g., "ravi" from "ravi/parsed_outputs/...")
        user_prefix = parsed_s3_key.split('/')[0]
        
        # # Create custom output path
        # from datetime import datetime
        # timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        # base_filename = Path(parsed_s3_key).stem.replace('_parsed', '')
        # output_key = f"{user_prefix}/aws_architecture_diagrams/{base_filename}_architecture_{timestamp}.json"
        
        # # Save to custom S3 path
        # print(f"[AWS-ARCH-TOOL] 💾 Saving to: {output_key}")
        # s3_client.put_object(
        #     Bucket=bucket,
        #     Key=output_key,
        #     Body=json.dumps(result, indent=2).encode('utf-8'),
        #     ContentType='application/json'
        # )
        
        # s3_path = f"s3://{bucket}/{output_key}"
        
        # print(f"[AWS-ARCH-TOOL] ✅ Architecture saved to: {s3_path}")
        
        return {
            'status': 'success',
            'output_key': output_key,
            'bucket': bucket,
            's3_path': s3_path,
            'architecture': result.get('architecture', {}),
            'metadata': result.get('metadata', {}),
            'message': f'AWS architecture generated successfully. Saved to: {output_key}'
        }
        
    except Exception as e:
        print(f"[AWS-ARCH-TOOL] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc(),
            'message': f'Failed to generate AWS architecture: {str(e)}'
        }


@tool
def pricing_estimation_tool(bucket: str, parsed_key: str, clarification_key: str) -> Dict[str, Any]:
    """
    Estimate pricing and funding requirements for the RFx proposal.
    
    Args:
        bucket: S3 bucket containing data
        parsed_key: S3 key to parsed RFx data
        clarification_key: S3 key to clarifications
    
    Returns:
        Detailed pricing breakdown with cost estimates and funding recommendations
    """
    try:
        from pricing_funding_agent import PricingFundingAgent
        
        agent = PricingFundingAgent()
        
        print(f"[TOOL] Estimating pricing from parsed={parsed_key}, clarifications={clarification_key}")
        result_key = agent.run(bucket, parsed_key, clarification_key, bucket)
        
        # Read pricing data
        response = s3_client.get_object(Bucket=bucket, Key=result_key)
        pricing_data = json.loads(response['Body'].read())
        
        return {
            'status': 'success',
            'output_key': result_key,
            'bucket': bucket,
            'pricing': pricing_data,
            'message': f'Pricing estimate completed. Output saved to: {result_key}'
        }
    except Exception as e:
        print(f"[ERROR] Pricing tool failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'message': f'Failed to estimate pricing: {str(e)}'
        }


@tool
def sow_drafting_tool(
    bucket: str,
    parsed_key: str,
    clarification_key: str,
    pricing_key: str
) -> Dict[str, Any]:
    """
    Draft a comprehensive Statement of Work (SOW) document.
    
    Args:
        bucket: S3 bucket containing data
        parsed_key: S3 key to parsed RFx data
        clarification_key: S3 key to clarifications
        pricing_key: S3 key to pricing estimates
    
    Returns:
        Complete SOW document with all sections
    """
    try:
        from sow_drafting_agent import SOWDraftingAgent
        
        agent = SOWDraftingAgent()
        
        print(f"[TOOL] Drafting SOW from parsed={parsed_key}, clarifications={clarification_key}, pricing={pricing_key}")
        result_key = agent.run(bucket, parsed_key, clarification_key, pricing_key, bucket)
        
        return {
            'status': 'success',
            'output_key': result_key,
            'bucket': bucket,
            'sow_s3_path': f"s3://{bucket}/{result_key}",
            'message': f'SOW draft completed. Document saved to: {result_key}'
        }
    except Exception as e:
        print(f"[ERROR] SOW tool failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'message': f'Failed to draft SOW: {str(e)}'
        }

ORCHESTRATOR_PROMPT = """You are an intelligent RFx (Request for Proposal/Quote/Information) processing orchestrator that coordinates specialized agents to automate proposal response workflows.

**Your Specialized Agents:**

1. **rfx_parsing_tool**: Extracts and structures content from RFx documents
   - Use for: Initial document processing, requirement extraction
   - Returns: parsed_data with output_key and bucket
   
2. **clarification_tool**: Generates clarification questions for ambiguous requirements
   - Use for: Identifying unclear specifications, generating questions for client
   - Returns: clarifications with output_key and bucket

3. **aws_architecture_generation_tool**: Generates AWS reference architectures
   - Use for: Creating AWS architecture diagrams based on technical requirements
   - Requires: parsed RFx output_key and clarification output_key
   - Searches: Knowledge Base (approved architectures) + MCP Server (AWS references)
   - Returns: Architecture diagram with S3 path

4. **pricing_estimation_tool**: Estimates costs and funding requirements
   - Use for: Budget planning, cost breakdown, resource allocation
   - Returns: pricing data with output_key and bucket

5. **sow_drafting_tool**: Creates comprehensive Statement of Work documents
   - Use for: Final proposal document generation
   - Returns: SOW document location

**Enhanced Workflow:**

When processing an RFx document:

1. **Start with parsing**: Parse the RFx document to extract structured data
   - Extract: parsed_key and bucket from result
   
2. **Generate clarifications**: Identify ambiguous requirements
   - Pass: bucket='presales-rfp-outputs' and parsed_key
   - Extract: clarification_key from result
   
3. **Generate AWS Architecture**:
   - Check if technical requirements and clarifications mention cloud/AWS infrastructure
   - If yes: Call aws_architecture_generation_tool
   - Pass: parsed_key and clarification_key (both from presales-rfp-outputs bucket)
   - Extract: architecture_key from result
   
4. **Estimate pricing**: Calculate costs
   - Pass: parsed_key, clarification_key, and architecture_key (if generated)
   - Use architecture for more accurate cloud cost estimates
   
5. **Draft SOW**: Create final proposal
   - Pass: parsed_key, clarification_key, pricing_key, and architecture_key (if available)
   - Include architecture diagram in SOW

**CRITICAL - S3 Path Management:**
- After parsing: bucket becomes 'presales-rfp-outputs'
- All subsequent tools should use 'presales-rfp-outputs' as the bucket
- Always use the output_key from the previous tool's response
- Architecture tool saves to: {user}/aws_architecture_diagrams/

**When to Generate Architecture:**
- Technical requirements mention: AWS, cloud, infrastructure, services, architecture
- Requirements can include: Lambda, S3, DynamoDB, EC2, or other AWS services
- Client asks for: scalable, serverless, microservices, or cloud-native solutions
- Skip if: No cloud/technical requirements present

**Best Practices:**
- Always pass output keys correctly between tools
- Use 'presales-rfp-outputs' bucket for all tools after parsing
- Provide status updates after each tool execution
- Generate architecture BEFORE pricing (for accurate estimates)
- If a tool fails, explain the error and suggest next steps
- Summarize key findings from each step

**Response Format:**
For each step, provide:
- ✅ Status (success/in-progress/error)
- 📊 Key findings or outputs
- ➡️ Next action in the pipeline

Maintain a professional, efficient tone suitable for enterprise proposal workflows."""


# ============================================
# Orchestrator Agent Configuration
# ============================================

# ORCHESTRATOR_PROMPT = """You are an intelligent RFx (Request for Proposal/Quote/Information) processing orchestrator that coordinates specialized agents to automate proposal response workflows.

# **Your Specialized Agents:**

# 1. **rfx_parsing_tool**: Extracts and structures content from RFx documents
#    - Use for: Initial document processing, requirement extraction
#    - Returns: parsed_data with output_key and bucket
   
# 2. **clarification_tool**: Generates clarification questions for ambiguous requirements
#    - Use for: Identifying unclear specifications, generating questions for client
#    - Returns: clarifications with output_key and bucket

# 3. **pricing_estimation_tool**: Estimates costs and funding requirements
#    - Use for: Budget planning, cost breakdown, resource allocation
#    - Returns: pricing data with output_key and bucket

# 4. **sow_drafting_tool**: Creates comprehensive Statement of Work documents
#    - Use for: Final proposal document generation
#    - Returns: SOW document location

# **Workflow Guidelines:**

# When processing an RFx document:

# 1. **Start with parsing**: Always begin by parsing the RFx document to extract structured data
#    - Extract the output_key and bucket from the result
   
# 2. **Generate clarifications**: Use the parsed output_key to identify ambiguous requirements
#    - Pass the output bucket (usually 'presales-rfp-outputs') and the parsed_key
   
# 3. **Estimate pricing**: Calculate costs based on requirements and clarifications
#    - Pass the parsed_key and clarification_key from previous steps
   
# 4. **Draft SOW**: Create the final proposal document incorporating all previous outputs
#    - Pass parsed_key, clarification_key, and pricing_key

# **CRITICAL - S3 Path Management:**
# - After parsing: bucket becomes 'presales-rfp-outputs'
# - All subsequent tools should use 'presales-rfp-outputs' as the bucket
# - Always use the output_key from the previous tool's response
# - Example flow:
#   * Parse: s3://presales-rfp-inputs/user/file.pdf → outputs to presales-rfp-outputs
#   * Clarify: use bucket='presales-rfp-outputs' and parsed_key from parse result
#   * Price: use bucket='presales-rfp-outputs' and keys from previous results
#   * SOW: use bucket='presales-rfp-outputs' and all previous keys

# **Best Practices:**
# - Always pass output keys correctly between tools
# - Use 'presales-rfp-outputs' bucket for all tools after parsing
# - Provide status updates after each tool execution
# - If a tool fails, explain the error and suggest next steps
# - Summarize key findings from each step

# **Response Format:**
# For each step, provide:
# - ✅ Status (success/in-progress/error)
# - 📊 Key findings or outputs
# - ➡️ Next action in the pipeline

# Maintain a professional, efficient tone suitable for enterprise proposal workflows."""

# Initialize Bedrock model
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name=os.environ.get('AWS_REGION', 'us-east-1'),
    temperature=0.3,
)

# Add conversation management
conversation_manager = SummarizingConversationManager(
    summary_ratio=0.3,
    preserve_recent_messages=5,
)

# Create the orchestrator agent
orchestrator_agent = Agent(
    model=bedrock_model,
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=[
        rfx_parsing_tool,
        clarification_tool,
        aws_architecture_generation_tool,
        pricing_estimation_tool,
        sow_drafting_tool,
    ],
    conversation_manager=conversation_manager,
)


# ============================================
# AgentCore Entrypoint
# ============================================

@app.entrypoint
async def invoke(payload: Dict[str, Any]):
    """
    Main entrypoint for AgentCore runtime.
    Supports streaming responses for real-time updates.
    
    Expected payload:
    {
        "prompt": "Process RFx document...",
        "bucket": "presales-rfp-inputs",
        "s3_key": "user/rfp.pdf",
        "action": "full_pipeline"
    }
    """
    """
    Main entrypoint for AgentCore runtime.
    Supports streaming responses for real-time updates.
    
    Supports both formats:
    
    NEW FORMAT (preferred):
    {
        "prompt": "Process RFx document...",
        "bucket": "presales-rfp-inputs",
        "s3_key": "user/rfp.pdf",
        "action": "full_pipeline"
    }
    
    OLD FORMAT (backward compatible):
    {
        "action": "runOrchestrator",
        "bucketIn": "presales-rfp-inputs",
        "inputKey": "user/rfp.pdf",
        "bucketOut": "presales-rfp-outputs"
    }
    """
    
    print(f"[INVOKE] Received payload: {json.dumps(payload, indent=2)}")
    
    # Handle backward compatibility with old wrapper format
    if "bucketIn" in payload or "inputKey" in payload:
        print("[INVOKE] Detected old wrapper format, converting...")
        bucket = payload.get("bucketIn", "presales-rfp-inputs")
        s3_key = payload.get("inputKey", "")
        action = "full_pipeline" if payload.get("action") == "runOrchestrator" else payload.get("action", "full_pipeline")
        user_message = ""
    else:
        # New format
        user_message = payload.get("prompt", "")
        bucket = payload.get("bucket", "presales-rfp-inputs")
        s3_key = payload.get("s3_key", "")
        action = payload.get("action", "full_pipeline")
    
    #print(f"[INVOKE] Received payload: {json.dumps(payload, indent=2)}")
    
    # # Extract parameters
    # user_message = payload.get("prompt", "")
    # bucket = payload.get("bucket", "presales-rfp-inputs")
    # s3_key = payload.get("s3_key", "")
    # action = payload.get("action", "full_pipeline")
    
    # Build the prompt
    if action == "full_pipeline" and s3_key:
        full_prompt = f"""Process the RFx document located at s3://{bucket}/{s3_key}.

Please execute the complete pipeline:
1. Parse the document using rfx_parsing_tool with bucket="{bucket}" and s3_key="{s3_key}"
2. Generate clarifications using clarification_tool with the parsed output
3. Generate AWS architecture using aws_architecture_generation_tool
4. Estimate pricing using pricing_estimation_tool (use architecture if available)
5. Draft SOW using sow_drafting_tool (include architecture diagram if available)

IMPORTANT: 
- After parsing, all subsequent tools should use bucket="presales-rfp-outputs"
- Use the output_key from each previous step
- Generate architecture ONLY if requirements and clarifications are present
- Architecture helps improve pricing accuracy

Provide updates as you complete each step."""
        
    else:
        full_prompt = user_message or f"Please process s3://{bucket}/{s3_key}"
    
    print(f"[INVOKE] Executing agent with prompt: {full_prompt[:200]}...")
    
    # Stream the agent's response
    try:
        async for event in orchestrator_agent.stream_async(full_prompt):
            if "data" in event:
                yield event["data"]
    except Exception as e:
        error_msg = f"Error during agent execution: {str(e)}"
        print(f"[ERROR] {error_msg}")
        yield json.dumps({"error": error_msg, "status": "failed"})


# ============================================
# Lambda Handler
# ============================================

def lambda_handler(event, context):
    """
    AWS Lambda handler that wraps the AgentCore app for streaming mode.
    """
    import asyncio
    
    print(f"[LAMBDA] Invocation started")
    print(f"[LAMBDA] Event: {json.dumps(event, indent=2)}")

    async def collect_stream():
        chunks = []
        try:
            async for chunk in invoke(event):
                chunks.append(chunk)
                print(f"[STREAM] Chunk received: {len(chunk)} bytes")
        except Exception as e:
            error_msg = f"Stream error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            chunks.append(json.dumps({"error": error_msg, "status": "failed"}))
        
        return "".join(chunks)

    try:
        result = asyncio.run(collect_stream())
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/plain",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            },
            "body": result
        }
    except Exception as e:
        error_msg = f"Lambda execution failed: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": error_msg,
                "status": "failed"
            })
        }


# ============================================
# Local Testing
# ============================================

if __name__ == "__main__":
    """
    For local testing with Strands CLI
    """
    print("🚀 Starting AgentCore app...")
    app.run()

       
    # # Option 2: Test locally with mock event
    # import json

    # # Simulate a Lambda event
    # event = {
    #     "invocation_type": "streaming",  # or "synchronous" if you want non-streaming
    #     "prompt": "Please process the RFx document at s3://presales-rfp-inputs/snehashri.pg/RFP_1.pdf.",
    #     "bucket": "presales-rfp-inputs",
    #     "s3_key": "snehashri.pg/RFP_1.pdf",
    #     "action": "full_pipeline"
    # }

    # print("🔹 Running Lambda simulation locally...\n")

    # # You don't need a real context object for local testing
    # response = lambda_handler(event, None)

    # print("\n\n🔹 Lambda Response:\n")
    # print(json.dumps(response, indent=2))