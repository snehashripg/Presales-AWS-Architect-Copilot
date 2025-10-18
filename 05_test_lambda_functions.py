#!/usr/bin/env python3
"""
Test Lambda Functions
Run in SageMaker: python 05_test_lambda_functions.py
"""

import boto3
import json
import time
from pathlib import Path

def test_lambda_function(lambda_client, function_name, test_payload):
    """Test a single Lambda function"""
    
    print(f"\n{'=' * 70}")
    print(f"🧪 Testing: {function_name}")
    print(f"{'=' * 70}")
    
    try:
        print(f"   📤 Invoking with payload...")
        print(f"   {json.dumps(test_payload, indent=6)}")
        
        start_time = time.time()
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        duration = time.time() - start_time
        
        # Parse response
        status_code = response['StatusCode']
        response_payload = json.loads(response['Payload'].read())
        
        print(f"\n   📥 Response received:")
        print(f"   ⏱️  Duration: {duration:.2f}s")
        print(f"   📊 Status Code: {status_code}")
        
        if status_code == 200:
            body = response_payload.get('body')
            if body:
                try:
                    body_json = json.loads(body) if isinstance(body, str) else body
                    print(f"   ✅ Success!")
                    print(f"   📝 Response: {json.dumps(body_json, indent=6)[:500]}...")
                    return True
                except:
                    print(f"   ✅ Response: {str(body)[:200]}...")
                    return True
            else:
                print(f"   ✅ Function executed successfully")
                return True
        else:
            print(f"   ⚠️  Non-200 status code")
            print(f"   📝 Response: {json.dumps(response_payload, indent=6)}")
            return False
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_functions():
    """Test all Lambda functions"""
    
    print("=" * 70)
    print("🧪 TEST LAMBDA FUNCTIONS")
    print("=" * 70)
    
    # Load Lambda functions info
    functions_file = Path.cwd() / "lambda_functions_info.json"
    if not functions_file.exists():
        print(f"\n❌ ERROR: lambda_functions_info.json not found")
        print(f"💡 Run 03_create_lambda_functions.py first!")
        return
    
    with open(functions_file, 'r') as f:
        functions_info = json.load(f)
    
    region = functions_info.get('region', 'us-east-1')
    lambda_client = boto3.client('lambda', region_name=region)
    
    print(f"\n📍 Region: {region}")
    print(f"⚡ Functions to test: {len(functions_info['functions'])}")
    
    # Test payloads for each function
    test_cases = {
        'rfx-orchestrator-function': {
            'action': 'runOrchestrator',
            'bucketIn': 'presales-rfp-inputs',
            'inputKey': 'ravi/RFP_1.pdf',
            'bucketOut': 'presales-rfp-outputs'
        },
        'rfx-parsing-function': {
            'action': 'parseRFP',
            'bucketIn': 'presales-rfp-inputs',
            'inputKey': 'ravi/RFP_1.pdf',
            'bucketOut': 'presales-rfp-outputs'
        },
        'rfx-clarification-function': {
            'action': 'generateClarifications',
            'bucketIn': 'presales-rfp-outputs',
            'parsedKey': 'ravi/parsed_outputs/RFP_1_parsed.json',
            'bucketOut': 'presales-rfp-outputs'
        },
        'rfx-pricing-function': {
            'action': 'estimatePricing',
            'bucketIn': 'presales-rfp-outputs',
            'parsedKey': 'ravi/parsed_outputs/RFP_1_parsed.json',
            'clarKey': 'ravi/clarifications/RFP_1_clarifications.json',
            'bucketOut': 'presales-rfp-outputs'
        },
        'rfx-sow-function': {
            'action': 'draftSOW',
            'bucketIn': 'presales-rfp-outputs',
            'parsedKey': 'ravi/parsed_outputs/RFP_1_parsed.json',
            'clarKey': 'ravi/clarifications/RFP_1_clarifications.json',
            'pricingKey': 'ravi/pricing_outputs/RFP_1_pricing.json',
            'bucketOut': 'presales-rfp-outputs'
        }
    }
    
    # Test each function
    results = {}
    
    for func in functions_info['functions']:
        func_name = func['name']
        
        if func_name in test_cases:
            test_payload = test_cases[func_name]
            success = test_lambda_function(lambda_client, func_name, test_payload)
            results[func_name] = success
        else:
            print(f"\n⚠️  No test case defined for: {func_name}")
            results[func_name] = None
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    
    for func_name, result in results.items():
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⚠️  SKIP"
        print(f"   {status} - {func_name}")
    
    print(f"\n📊 Results: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed == 0 and passed > 0:
        print(f"\n✅ ALL TESTS PASSED!")
        print(f"\n💡 Next: Test from Cloud9 frontend")
    elif failed > 0:
        print(f"\n⚠️  SOME TESTS FAILED - Check CloudWatch logs for details")
    
    return results


if __name__ == "__main__":
    try:
        results = test_all_functions()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

