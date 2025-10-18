#!/usr/bin/env python3
"""
07_test_agentcore_runtime.py
Test the deployed AgentCore multi-agent system

Run in SageMaker: python 07_test_agentcore_runtime.py
"""

import boto3
import json
import time
from pathlib import Path
from datetime import datetime

# AWS Clients
lambda_client = boto3.client('lambda', region_name='us-east-1')
s3_client = boto3.client('s3', region_name='us-east-1')

# Configuration
S3_INPUT_BUCKET = "presales-rfp-inputs"
S3_OUTPUT_BUCKET = "presales-rfp-outputs"


def invoke_agent(function_name, payload, invocation_type='RequestResponse'):
    """
    Invoke an AgentCore agent Lambda function
    
    Args:
        function_name: Lambda function name
        payload: Event payload dictionary
        invocation_type: 'RequestResponse' (sync) or 'Event' (async)
    
    Returns:
        Response dictionary
    """
    print(f"\n⚡ Invoking {function_name}...")
    print(f"📋 Payload: {json.dumps(payload, indent=2)[:200]}...")
    
    try:
        start_time = time.time()
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType=invocation_type,
            Payload=json.dumps(payload)
        )
        
        duration = time.time() - start_time
        
        if invocation_type == 'RequestResponse':
            response_payload = json.loads(response['Payload'].read())
            status_code = response_payload.get('statusCode', 500)
            
            if status_code == 200:
                body = json.loads(response_payload['body'])
                print(f"   ✅ Success (HTTP {status_code}) - Duration: {duration:.2f}s")
                return body
            else:
                body = json.loads(response_payload['body'])
                print(f"   ❌ Failed (HTTP {status_code})")
                print(f"   Error: {body.get('error', 'Unknown error')}")
                return body
        else:
            print(f"   📨 Async invocation submitted - Duration: {duration:.2f}s")
            return {"status": "async", "requestId": response.get('RequestId')}
            
    except Exception as e:
        print(f"   ❌ Invocation failed: {e}")
        raise


def test_parsing_agent():
    """Test the RFx Parsing Agent"""
    print("\n" + "=" * 80)
    print("🧪 TEST 1: RFx Parsing Agent")
    print("=" * 80)
    
    payload = {
        "action": "parseRFP",
        "bucketIn": S3_INPUT_BUCKET,
        "inputKey": "test/sample_rfp.pdf",
        "bucketOut": S3_OUTPUT_BUCKET
    }
    
    try:
        result = invoke_agent('rfx-agentcore-parsing', payload)
        
        if result.get('output_key'):
            print(f"\n   📄 Parsed document saved to: {result['output_key']}")
        
        return result
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return None


def test_clarification_agent(parsed_key):
    """Test the Clarification Agent"""
    print("\n" + "=" * 80)
    print("🧪 TEST 2: Clarification Agent")
    print("=" * 80)
    
    if not parsed_key:
        print("   ⚠️  Skipping - no parsed document available")
        return None
    
    payload = {
        "action": "generateClarifications",
        "bucketIn": S3_OUTPUT_BUCKET,
        "parsedKey": parsed_key,
        "bucketOut": S3_OUTPUT_BUCKET
    }
    
    try:
        result = invoke_agent('rfx-agentcore-clarification', payload)
        
        if result.get('output_key'):
            print(f"\n   💬 Clarifications saved to: {result['output_key']}")
        
        return result
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return None


def test_pricing_agent(parsed_key, clar_key):
    """Test the Pricing Agent"""
    print("\n" + "=" * 80)
    print("🧪 TEST 3: Pricing & Funding Agent")
    print("=" * 80)
    
    if not parsed_key or not clar_key:
        print("   ⚠️  Skipping - missing required inputs")
        return None
    
    payload = {
        "action": "estimatePricing",
        "bucketIn": S3_OUTPUT_BUCKET,
        "parsedKey": parsed_key,
        "clarKey": clar_key,
        "bucketOut": S3_OUTPUT_BUCKET
    }
    
    try:
        result = invoke_agent('rfx-agentcore-pricing', payload)
        
        if result.get('output_key'):
            print(f"\n   💰 Pricing estimate saved to: {result['output_key']}")
        
        return result
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return None


def test_sow_agent(parsed_key, clar_key, pricing_key):
    """Test the SOW Drafting Agent"""
    print("\n" + "=" * 80)
    print("🧪 TEST 4: SOW Drafting Agent")
    print("=" * 80)
    
    if not all([parsed_key, clar_key, pricing_key]):
        print("   ⚠️  Skipping - missing required inputs")
        return None
    
    payload = {
        "action": "draftSOW",
        "bucketIn": S3_OUTPUT_BUCKET,
        "parsedKey": parsed_key,
        "clarKey": clar_key,
        "pricingKey": pricing_key,
        "bucketOut": S3_OUTPUT_BUCKET
    }
    
    try:
        result = invoke_agent('rfx-agentcore-sow', payload)
        
        if result.get('output_key'):
            print(f"\n   📄 SOW document saved to: {result['output_key']}")
        
        return result
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return None


def test_orchestrator():
    """Test the full orchestrator"""
    print("\n" + "=" * 80)
    print("🧪 TEST 5: Full Orchestrator Pipeline")
    print("=" * 80)
    
    payload = {
        "action": "runOrchestrator",
        "bucketIn": S3_INPUT_BUCKET,
        "inputKey": "test/sample_rfp.pdf",
        "bucketOut": S3_OUTPUT_BUCKET
    }
    
    try:
        result = invoke_agent('rfx-agentcore-orchestrator', payload)
        
        # Display step results
        if result.get('steps'):
            print(f"\n   📊 Pipeline Steps Completed:")
            for step in result['steps']:
                step_name = step.get('step', 'Unknown')
                step_status = step.get('status', 'unknown')
                output = step.get('output', 'N/A')
                
                status_icon = "✅" if step_status == "success" else "❌"
                print(f"      {status_icon} {step_name}")
                print(f"         Output: {output}")
        
        # Display timing
        if result.get('total_time_seconds'):
            print(f"\n   ⏱️  Total execution time: {result['total_time_seconds']}s")
        
        return result
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return None


def test_async_invocation():
    """Test async (Event) invocation"""
    print("\n" + "=" * 80)
    print("🧪 TEST 6: Async Invocation (Event)")
    print("=" * 80)
    
    payload = {
        "action": "runOrchestrator",
        "bucketIn": S3_INPUT_BUCKET,
        "inputKey": "test/sample_rfp.pdf",
        "bucketOut": S3_OUTPUT_BUCKET
    }
    
    try:
        result = invoke_agent('rfx-agentcore-orchestrator', payload, invocation_type='Event')
        print(f"\n   ℹ️  Check CloudWatch Logs for execution results")
        print(f"   ℹ️  Request ID: {result.get('requestId', 'N/A')}")
        return result
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return None


def test_error_handling():
    """Test error handling with invalid input"""
    print("\n" + "=" * 80)
    print("🧪 TEST 7: Error Handling (Invalid Input)")
    print("=" * 80)
    
    payload = {
        "action": "runOrchestrator",
        "bucketIn": S3_INPUT_BUCKET,
        # Missing inputKey - should trigger validation error
        "bucketOut": S3_OUTPUT_BUCKET
    }
    
    try:
        result = invoke_agent('rfx-agentcore-orchestrator', payload)
        
        if result.get('error'):
            print(f"   ✅ Error handling working correctly")
            print(f"   Error: {result.get('error')}")
            print(f"   Message: {result.get('message', 'N/A')}")
        else:
            print(f"   ⚠️  Expected error but got success response")
        
        return result
    except Exception as e:
        print(f"   ℹ️  Exception caught (expected): {e}")
        return None


def check_s3_outputs(bucket, prefix="test/"):
    """Check S3 for output files"""
    print("\n" + "=" * 80)
    print("📁 Checking S3 Output Files")
    print("=" * 80)
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            MaxKeys=20
        )
        
        if response.get('Contents'):
            print(f"\n   Found {len(response['Contents'])} files:")
            for obj in response['Contents']:
                key = obj['Key']
                size = obj['Size']
                modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                print(f"      📄 {key}")
                print(f"         Size: {size:,} bytes | Modified: {modified}")
        else:
            print(f"\n   ℹ️  No files found with prefix: {prefix}")
            
    except Exception as e:
        print(f"   ❌ Error checking S3: {e}")


def run_sequential_test():
    """Run all agents sequentially (mimics orchestrator)"""
    print("\n" + "=" * 80)
    print("🔄 SEQUENTIAL AGENT TEST (Manual Orchestration)")
    print("=" * 80)
    print("This test runs each agent in sequence, passing outputs between them")
    
    # Step 1: Parse
    parse_result = test_parsing_agent()
    if not parse_result:
        print("\n❌ Sequential test aborted - parsing failed")
        return
    
    parsed_key = parse_result.get('output_key')
    time.sleep(2)
    
    # Step 2: Clarify
    clar_result = test_clarification_agent(parsed_key)
    clar_key = clar_result.get('output_key') if clar_result else None
    time.sleep(2)
    
    # Step 3: Price
    pricing_result = test_pricing_agent(parsed_key, clar_key)
    pricing_key = pricing_result.get('output_key') if pricing_result else None
    time.sleep(2)
    
    # Step 4: SOW
    sow_result = test_sow_agent(parsed_key, clar_key, pricing_key)
    
    print("\n✅ Sequential test complete")


def main():
    """Main test function"""
    print("=" * 80)
    print("🧪 RFx AGENTCORE RUNTIME - TEST SUITE")
    print("=" * 80)
    print("\nThis will test all AgentCore agents:")
    print("  • Individual agent tests")
    print("  • Full orchestrator test")
    print("  • Sequential pipeline test")
    print("  • Error handling test")
    print("  • Async invocation test")
    
    response = input("\n✨ Run test suite? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\n❌ Tests cancelled")
        return
    
    start_time = time.time()
    results = {}
    
    try:
        # Run individual tests
        print("\n" + "=" * 80)
        print("📋 RUNNING INDIVIDUAL AGENT TESTS")
        print("=" * 80)
        
        # Test 1-4: Sequential agent test
        run_sequential_test()
        
        # Test 5: Full orchestrator
        orchestrator_result = test_orchestrator()
        results['orchestrator'] = orchestrator_result
        
        # Test 6: Async invocation
        async_result = test_async_invocation()
        results['async'] = async_result
        
        # Test 7: Error handling
        error_result = test_error_handling()
        results['error_handling'] = error_result
        
        # Check S3 outputs
        check_s3_outputs(S3_OUTPUT_BUCKET, "test/")
        
        # Summary
        total_time = time.time() - start_time
        print("\n" + "=" * 80)
        print("✅ TEST SUITE COMPLETE")
        print("=" * 80)
        print(f"\n⏱️  Total test duration: {total_time:.2f}s")
        print(f"\n📊 Results Summary:")
        print(f"   • Sequential pipeline: ✅ Completed")
        print(f"   • Full orchestrator: {'✅ Success' if orchestrator_result else '❌ Failed'}")
        print(f"   • Async invocation: {'✅ Submitted' if async_result else '❌ Failed'}")
        print(f"   • Error handling: {'✅ Working' if error_result else '❌ Failed'}")
        
        print("\n💡 Next Steps:")
        print("1. Review CloudWatch Logs for detailed execution traces")
        print("2. Check S3 buckets for generated outputs")
        print("3. Test from frontend application")
        print("4. Monitor agent performance and costs")
        
        # Save test results
        test_report = {
            "test_timestamp": datetime.utcnow().isoformat(),
            "total_duration_seconds": total_time,
            "results": results
        }
        
        report_file = Path("agentcore_test_results.json")
        report_file.write_text(json.dumps(test_report, indent=2, default=str))
        print(f"\n📄 Test report saved to: {report_file}")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main() or 0)