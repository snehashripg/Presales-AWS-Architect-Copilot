#!/usr/bin/env python3
"""
Master AgentCore Deployment Script
Run in SageMaker: python 00_deploy_agentcore.py
"""

import subprocess
import sys
from pathlib import Path


def run_script(script_name, description):
    """Run a Python script and handle errors"""
    
    print("\n" + "=" * 70)
    print(f"🚀 {description}")
    print("=" * 70)
    
    script_path = Path.cwd() / script_name
    
    if not script_path.exists():
        print(f"❌ Script not found: {script_name}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=False
        )
        
        print(f"\n✅ {description} - COMPLETED")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} - FAILED")
        print(f"Error code: {e.returncode}")
        return False
    except Exception as e:
        print(f"\n❌ {description} - FAILED: {e}")
        return False


def main():
    """Run all AgentCore deployment steps"""
    
    print("=" * 70)
    print("🚀 RFx AGENTCORE - COMPLETE DEPLOYMENT")
    print("=" * 70)
    print("\nThis will deploy the AgentCore-based orchestrator:")
    print("  1. Package AgentCore Lambda Layer")
    print("  2. Upload and Create Layer")
    print("  3. Create AgentCore Lambda Function")
    print("  4. Configure Cognito Permissions")
    print("  5. Test AgentCore Lambda Function")
    
    print("\n⚡ Key Differences from Standard Deployment:")
    print("   • Single Lambda function (not 5 separate functions)")
    print("   • Uses Strands AgentCore framework")
    print("   • Streaming support enabled")
    print("   • Dynamic tool orchestration")
    
    response = input("\nProceed with AgentCore deployment? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\n❌ Deployment cancelled")
        return
    
    # Deployment steps
    steps = [
        ("01_package_agentcore_layer.py", "Package AgentCore Lambda Layer"),
        ("02_upload_agentcore_layer.py", "Upload and Create AgentCore Layer"),
        ("03_create_agentcore_function.py", "Create AgentCore Lambda Function"),
        ("04_configure_cognito_agentcore.py", "Configure Cognito Permissions"),
        ("test_agentcore_lambda.py", "Test AgentCore Lambda Function")
    ]
    
    results = []
    
    for script, description in steps:
        success = run_script(script, description)
        results.append((description, success))
        
        if not success:
            print(f"\n⚠️  Step failed: {description}")
            response = input("Continue with next step anyway? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("\n❌ Deployment stopped")
                break
    
    # Final summary
    print("\n" + "=" * 70)
    print("📊 AGENTCORE DEPLOYMENT SUMMARY")
    print("=" * 70)
    
    for description, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {description}")
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    print(f"\n📊 Completed: {passed}/{total} steps")
    
    if passed == total:
        print("\n" + "=" * 70)
        print("🎉 AGENTCORE DEPLOYMENT COMPLETE!")
        print("=" * 70)
        print("\n✅ AgentCore orchestrator deployed and configured")
        print("✅ Cognito permissions set up")
        print("✅ Ready for testing")
        
        print("\n💡 What You Get with AgentCore:")
        print("   • Streaming responses for real-time updates")
        print("   • Dynamic tool orchestration")
        print("   • Single function handles all RFx workflows")
        print("   • Better error handling and retry logic")
        print("   • Conversation memory across requests")
        
        print("\n💡 Next Steps:")
        print("1. Review CloudWatch logs for the Lambda function")
        print("2. Check S3 bucket: presales-rfp-outputs for test outputs")
        print("3. Update Cloud9 frontend to call:")
        print("   Function: rfx-agentcore-orchestrator")
        print("   Payload: {bucket, s3_key, action: 'full_pipeline'}")
        print("4. Test streaming responses in your UI")
        
        print("\n📚 Frontend Integration Example:")
        print("""
const payload = {
    bucket: 'presales-rfp-inputs',
    s3_key: 'user/document.pdf',
    action: 'full_pipeline'
};

const result = await lambda.invoke({
    FunctionName: 'rfx-agentcore-orchestrator',
    Payload: JSON.stringify(payload)
}).promise();

const response = JSON.parse(result.Payload);
console.log(response.body); // Streaming output
        """)
    else:
        print("\n⚠️  DEPLOYMENT INCOMPLETE")
        print("\nSome steps failed. Review the errors above and:")
        print("1. Fix any issues")
        print("2. Re-run failed steps individually")
        print("3. Or run 00_deploy_agentcore.py again")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Deployment cancelled by user")
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()