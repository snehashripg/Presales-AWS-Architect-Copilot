#!/usr/bin/env python3
"""
Test AgentCore Lambda Function
Run in SageMaker: python test_agentcore_lambda.py
"""

import boto3
import json
from pathlib import Path
from datetime import datetime


def test_agentcore_lambda():
    """Test the AgentCore Lambda function"""
    
    print("=" * 70)
    print("🧪 TEST AGENTCORE LAMBDA FUNCTION")
    print("=" * 70)
    
    # Load function info
    functions_file = Path.cwd() / "agentcore_function_info.json"
    if not functions_file.exists():
        print(f"\n❌ ERROR: agentcore_function_info.json not found")
        print(f"💡 Run 03_create_agentcore_function.py first!")
        return
    
    with open(functions_file, 'r') as f:
        function_info = json.load(f)
    
    function_name = function_info['name']
    region = function_info['region']
    
    print(f"\n📝 Function: {function_name}")
    print(f"🌍 Region: {region}")
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Test cases
    test_cases = [
        {
            "name": "Full Pipeline Test (New Format)",
            "payload": {
                "bucket": "presales-rfp-inputs",
                "s3_key": "test/RFP_5.pdf",
                "action": "full_pipeline",
                "prompt": "Process the complete RFx pipeline for this document"
            }
        },
        {
            "name": "Full Pipeline Test (Old Wrapper Format - Backward Compatible)",
            "payload": {
                "action": "runOrchestrator",
                "bucketIn": "presales-rfp-inputs",
                "inputKey": "test/RFP_5.pdf",
                "bucketOut": "presales-rfp-outputs"
            }
        },
        {
            "name": "Custom Prompt Test",
            "payload": {
                "bucket": "presales-rfp-inputs",
                "s3_key": "test/RFP_5.pdf",
                "prompt": "Parse this RFx document and generate clarification questions only"
            }
        }
    ]
    
    print(f"\n🧪 Running {len(test_cases)} test cases...")
    
    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 70}")
        print(f"TEST {idx}/{len(test_cases)}: {test_case['name']}")
        print(f"{'=' * 70}")
        
        payload = test_case['payload']
        print(f"\n📤 Payload:")
        print(json.dumps(payload, indent=2))
        
        try:
            print(f"\n⏳ Invoking Lambda function...")
            start_time = datetime.now()
            
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',  # Synchronous
                Payload=json.dumps(payload)
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Read response
            response_payload = json.loads(response['Payload'].read().decode('utf-8'))
            status_code = response_payload.get('statusCode', 500)
            
            print(f"\n📊 Response Status: {status_code}")
            print(f"⏱️  Duration: {duration:.2f}s")
            
            if status_code == 200:
                body = response_payload.get('body', '')
                print(f"\n✅ Test PASSED")
                print(f"\n📝 Response Preview (first 500 chars):")
                print(body[:500])
                
                if len(body) > 500:
                    print(f"\n... (truncated, total length: {len(body)} chars)")
                
                # Try to identify key outputs
                if 'parsed' in body.lower():
                    print(f"\n   ✅ Parsing step detected")
                if 'clarification' in body.lower():
                    print(f"   ✅ Clarification step detected")
                if 'pricing' in body.lower():
                    print(f"   ✅ Pricing step detected")
                if 'sow' in body.lower():
                    print(f"   ✅ SOW drafting step detected")
                
            else:
                print(f"\n❌ Test FAILED")
                print(f"\n📝 Error Response:")
                print(json.dumps(response_payload, indent=2))
            
        except Exception as e:
            print(f"\n❌ Test FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n{'=' * 70}")
    print("🏁 TEST SUMMARY")
    print(f"{'=' * 70}")
    print(f"\n✅ All tests completed")
    print(f"\n💡 Next Steps:")
    print("   1. Review the logs in CloudWatch")
    print("   2. Check S3 outputs in presales-rfp-outputs bucket")
    print("   3. Test from Cloud9 frontend")
    print("   4. Monitor for streaming responses")


def test_quick_invocation():
    """Quick test with minimal payload"""
    
    print("\n" + "=" * 70)
    print("🚀 QUICK INVOCATION TEST")
    print("=" * 70)
    
    # Load function info
    functions_file = Path.cwd() / "agentcore_function_info.json"
    if not functions_file.exists():
        print(f"\n❌ ERROR: agentcore_function_info.json not found")
        return
    
    with open(functions_file, 'r') as f:
        function_info = json.load(f)
    
    function_name = function_info['name']
    region = function_info['region']
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Simple test payload
    payload = {
        "prompt": "Hello, can you help me process an RFx document?",
        "bucket": "presales-rfp-inputs",
        "s3_key": "test/sample.pdf"
    }
    
    print(f"\n📤 Testing basic connectivity...")
    print(f"Function: {function_name}")
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        
        if result.get('statusCode') == 200:
            print(f"\n✅ Lambda function is responsive!")
            print(f"📝 Response preview: {result.get('body', '')[:200]}")
        else:
            print(f"\n⚠️  Lambda responded but with error:")
            print(json.dumps(result, indent=2))
            
    except Exception as e:
        print(f"\n❌ Failed to invoke Lambda: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        test_quick_invocation()
    else:
        try:
            test_agentcore_lambda()
        except KeyboardInterrupt:
            print("\n\n❌ Test cancelled by user")
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()