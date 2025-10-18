# agentcore_wrapper.py
"""
AgentCore wrapper to host RFx Orchestrator Agent
This makes your agent accessible via Lambda

USAGE:
1. Copy this file to ~/SageMaker/backend/
2. Test: python -c "from agentcore_wrapper import lambda_handler; print('OK')"
3. Package with other agents and deploy to Lambda
"""

import json
import os
import traceback
from datetime import datetime


class AgentCoreHandler:
    """
    Handler class for AgentCore integration
    Hosts all RFx Agents and makes them callable via Lambda
    """
    
    def __init__(self):
        """Initialize agents based on AGENT_TYPE environment variable"""
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        self.agent_type = os.environ.get('AGENT_TYPE', 'orchestrator')
        
        # Import and initialize the appropriate agent
        if self.agent_type == 'orchestrator':
            from rfx_orchestrator_agent import RFxOrchestratorAgent
            self.agent = RFxOrchestratorAgent(region=self.region)
        elif self.agent_type == 'parsing':
            from rfx_parsing_agent import RFxParsingAgent
            self.agent = RFxParsingAgent(region=self.region)
        elif self.agent_type == 'clarification':
            from clarification_agent import ClarificationAgent
            self.agent = ClarificationAgent(region=self.region)
        elif self.agent_type == 'pricing':
            from pricing_funding_agent import PricingFundingAgent
            self.agent = PricingFundingAgent(region=self.region)
        elif self.agent_type == 'sow':
            from sow_drafting_agent import SOWDraftingAgent
            self.agent = SOWDraftingAgent(region=self.region)
        else:
            # Default to orchestrator
            from rfx_orchestrator_agent import RFxOrchestratorAgent
            self.agent = RFxOrchestratorAgent(region=self.region)
        
        print(f"[INFO] AgentCore Handler initialized (type: {self.agent_type}, region: {self.region})")
    
    def process_request(self, event):
        """
        Main handler for AgentCore requests
        
        Args:
            event (dict): Lambda event containing:
                - action (str): Action to perform (e.g., 'runOrchestrator', 'parseRFP', etc.)
                - bucketIn (str): Input S3 bucket
                - inputKey (str): S3 key for input file (required for orchestrator/parsing)
                - bucketOut (str): Output S3 bucket
                - modelId (str): Bedrock model ID (optional)
                - enableGuardrails (bool): Enable guardrails (optional)
                
                Agent-specific parameters:
                - parsedKey (str): For clarification/pricing/sow agents
                - clarKey (str): For pricing/sow agents
                - pricingKey (str): For sow agent
        
        Returns:
            dict: Lambda response with statusCode and body
        
        Example events:
        Orchestrator: {"action": "runOrchestrator", "bucketIn": "...", "inputKey": "...", "bucketOut": "..."}
        Parsing: {"action": "parseRFP", "bucketIn": "...", "inputKey": "...", "bucketOut": "..."}
        Clarification: {"action": "generateClarifications", "bucketIn": "...", "parsedKey": "...", "bucketOut": "..."}
        Pricing: {"action": "estimatePricing", "bucketIn": "...", "parsedKey": "...", "clarKey": "...", "bucketOut": "..."}
        SOW: {"action": "draftSOW", "bucketIn": "...", "parsedKey": "...", "clarKey": "...", "pricingKey": "...", "bucketOut": "..."}
        """
        try:
            # Extract parameters from event
            action = event.get('action', 'runOrchestrator')
            bucket_in = event.get('bucketIn', os.environ.get('S3_INPUT_BUCKET', 'presales-rfp-inputs'))
            input_key = event.get('inputKey')
            bucket_out = event.get('bucketOut', os.environ.get('S3_OUTPUT_BUCKET', 'presales-rfp-outputs'))
            model_id = event.get('modelId', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
            enable_guardrails = event.get('enableGuardrails', False)
            
            # Validate required parameters
            if not input_key:
                raise ValueError("inputKey is required in the event payload")
            
            # Log execution details
            print(f"[INFO] ========================================")
            print(f"[INFO] AgentCore Request Processing Started")
            print(f"[INFO] ========================================")
            print(f"[INFO] Action: {action}")
            print(f"[INFO] Input: s3://{bucket_in}/{input_key}")
            print(f"[INFO] Output: s3://{bucket_out}")
            print(f"[INFO] Model: {model_id}")
            print(f"[INFO] Guardrails: {enable_guardrails}")
            print(f"[INFO] ========================================")
            
            # Execute the appropriate agent based on type
            print(f"[INFO] Starting {self.agent_type} agent...")
            
            if self.agent_type == 'orchestrator':
                result = self.agent.run(bucket_in, input_key, bucket_out)
            
            elif self.agent_type == 'parsing':
                result = {'output_key': self.agent.run(bucket_in, input_key, bucket_out)}
            
            elif self.agent_type == 'clarification':
                parsed_key = event.get('parsedKey', input_key)
                result = {'output_key': self.agent.run(bucket_in, parsed_key, bucket_out)}
            
            elif self.agent_type == 'pricing':
                parsed_key = event.get('parsedKey')
                clar_key = event.get('clarKey')
                if not parsed_key or not clar_key:
                    raise ValueError("parsedKey and clarKey are required for pricing agent")
                result = {'output_key': self.agent.run(bucket_in, parsed_key, clar_key, bucket_out)}
            
            elif self.agent_type == 'sow':
                parsed_key = event.get('parsedKey')
                clar_key = event.get('clarKey')
                pricing_key = event.get('pricingKey')
                if not all([parsed_key, clar_key, pricing_key]):
                    raise ValueError("parsedKey, clarKey, and pricingKey are required for SOW agent")
                result = {'output_key': self.agent.run(bucket_in, parsed_key, clar_key, pricing_key, bucket_out)}
            
            else:
                # Default to orchestrator
                result = self.agent.run(bucket_in, input_key, bucket_out)
            
            # Ensure result is a dictionary
            if not isinstance(result, dict):
                result = {'output': str(result)}
            
            # Add AgentCore metadata to result
            result['agentcore_metadata'] = {
                'timestamp': datetime.utcnow().isoformat(),
                'action': action,
                'model_id': model_id,
                'guardrails_enabled': enable_guardrails,
                'status': 'success'
            }
            
            print(f"[INFO] ========================================")
            print(f"[INFO] AgentCore Request Completed Successfully")
            print(f"[INFO] Status: {result.get('status', 'unknown')}")
            print(f"[INFO] Total Steps: {len(result.get('steps', []))}")
            print(f"[INFO] ========================================")
            
            # Return successful response
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                },
                'body': json.dumps(result)
            }
            
        except ValueError as ve:
            # Validation error
            error_msg = str(ve)
            print(f"[ERROR] Validation Error: {error_msg}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Validation Error',
                    'message': error_msg,
                    'status': 'failed'
                })
            }
            
        except Exception as e:
            # Unexpected error
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            print(f"[ERROR] ========================================")
            print(f"[ERROR] AgentCore Request Failed")
            print(f"[ERROR] ========================================")
            print(f"[ERROR] Error: {error_msg}")
            print(f"[ERROR] Trace:\n{error_trace}")
            print(f"[ERROR] ========================================")
            
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Internal Server Error',
                    'message': error_msg,
                    'trace': error_trace,
                    'status': 'failed'
                })
            }


# Global handler instance (initialized once per Lambda container)
handler = AgentCoreHandler()


def lambda_handler(event, context):
    """
    Lambda entry point for AgentCore invocations
    
    This function is called by AWS Lambda when the function is invoked.
    It delegates to the AgentCoreHandler for actual processing.
    
    Args:
        event (dict): Lambda event payload
        context (object): Lambda context object
    
    Returns:
        dict: Lambda response
    """
    print(f"[INFO] Lambda invocation started")
    print(f"[INFO] Request ID: {context.aws_request_id}")
    print(f"[INFO] Function Name: {context.function_name}")
    print(f"[INFO] Remaining Time: {context.get_remaining_time_in_millis()}ms")
    
    # Process the request
    response = handler.process_request(event)
    
    # Add Lambda context to response if successful
    if response['statusCode'] == 200:
        try:
            body = json.loads(response['body'])
            body['lambda_metadata'] = {
                'request_id': context.request_id,
                'function_name': context.function_name,
                'log_group': context.log_group_name,
                'log_stream': context.log_stream_name
            }
            response['body'] = json.dumps(body)
        except:
            pass  # If we can't add metadata, that's okay
    
    print(f"[INFO] Lambda invocation completed with status: {response['statusCode']}")
    return response


# For local testing
if __name__ == "__main__":
    """
    Local testing - simulates Lambda invocation
    
    Run: python agentcore_wrapper.py
    """
    print("[TEST] Testing AgentCore Wrapper locally...")
    
    # Create mock Lambda context
    class MockContext:
        request_id = "test-request-123"
        function_name = "rfx-agentcore-orchestrator-test"
        log_group_name = "/aws/lambda/test"
        log_stream_name = "test-stream"
        
        def get_remaining_time_in_millis(self):
            return 900000  # 15 minutes
    
    # Create test event
    test_event = {
        "action": "runOrchestrator",
        "bucketIn": "presales-rfp-inputs",
        "inputKey": "ravi/RFP_1.pdf",
        "bucketOut": "presales-rfp-outputs"
    }
    
    # Test the handler
    print("[TEST] Event:", json.dumps(test_event, indent=2))
    print("[TEST] Invoking handler...")
    
    try:
        response = lambda_handler(test_event, MockContext())
        print("[TEST] Response Status:", response['statusCode'])
        print("[TEST] Response Body:", response['body'][:200] + "..." if len(response['body']) > 200 else response['body'])
        print("[TEST] ✅ Test completed successfully!")
    except Exception as e:
        print(f"[TEST] ❌ Test failed: {e}")
        traceback.print_exc()

