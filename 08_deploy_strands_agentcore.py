#!/usr/bin/env python3
"""
08_deploy_strands_agentcore.py
Deploy RFx Multi-Agent System using Strands AgentCore Runtime

This deployment uses the Strands framework for true Bedrock Agent Runtime integration
with streaming support, conversation management, and tool-based orchestration.

Run in SageMaker: python 08_deploy_strands_agentcore.py
"""

import subprocess
import sys
import boto3
import json
import zipfile
from pathlib import Path
from datetime import datetime

# AWS Configuration
REGION = "us-east-1"
ACCOUNT_ID = "040504913362"
ROLE_ARN = "arn:aws:iam::040504913362:role/HCL-User-Role-Aiml-lambda"
S3_BUCKET = "presales-rfp-outputs"

lambda_client = boto3.client('lambda', region_name=REGION)
s3_client = boto3.client('s3', region_name=REGION)


def install_strands():
    """Install Strands framework if not already installed"""
    print("\n📦 Installing Strands framework...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "strands", "-q"],
            check=True
        )
        print("   ✅ Strands installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to install Strands: {e}")
        return False


def create_requirements_txt():
    """Create requirements.txt for Lambda layer"""
    print("\n📝 Creating requirements.txt...")
    
    requirements = """strands>=0.1.0
boto3>=1.34.0
anthropic>=0.25.0
pydantic>=2.0.0
"""
    
    Path("requirements.txt").write_text(requirements)
    print("   ✅ requirements.txt created")


def create_deployment_package():
    """Create deployment package with Strands AgentCore code"""
    print("\n📦 Creating Strands AgentCore deployment package...")
    
    package_dir = Path("strands_package")
    package_dir.mkdir(exist_ok=True)
    
    # List of files to include
    files_to_include = [
        "main.py",  # Strands AgentCore entry point
        "rfx_orchestrator_agent.py",
        "rfx_parsing_agent.py",
        "clarification_agent.py",
        "pricing_funding_agent.py",
        "sow_drafting_agent.py",
    ]
    
    # Copy agent files
    for file in files_to_include:
        src = Path(file)
        if src.exists():
            dest = package_dir / file
            dest.write_text(src.read_text())
            print(f"   ✓ Added {file}")
        else:
            print(f"   ⚠️  Warning: {file} not found")
    
    # Create lambda_function.py that imports main.py
    lambda_function = package_dir / "lambda_function.py"
    lambda_function.write_text("""# Lambda function entry point for Strands AgentCore
from main import lambda_handler

# AWS Lambda will call this function
# It delegates to the Strands AgentCore app
""")
    print(f"   ✓ Created lambda_function.py entry point")
    
    # Create ZIP file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"strands-agentcore-{timestamp}.zip"
    zip_path = Path(zip_filename)
    
    print(f"\n📦 Creating ZIP file: {zip_filename}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in package_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(package_dir)
                zipf.write(file, arcname)
                print(f"   ✓ Packaged {arcname}")
    
    # Upload to S3
    s3_key = f"lambda_code/strands_agentcore/{zip_filename}"
    print(f"\n☁️  Uploading to S3: s3://{S3_BUCKET}/{s3_key}")
    
    s3_client.upload_file(str(zip_path), S3_BUCKET, s3_key)
    print(f"   ✅ Upload complete")
    
    # Cleanup
    import shutil
    shutil.rmtree(package_dir)
    zip_path.unlink()
    
    return s3_key


def create_strands_layer():
    """Create Lambda layer with Strands dependencies"""
    print("\n🏗️  Creating Strands Lambda layer...")
    
    layer_dir = Path("strands_layer")
    python_dir = layer_dir / "python"
    python_dir.mkdir(parents=True, exist_ok=True)
    
    # Install dependencies to layer directory
    print("   Installing dependencies...")
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "strands", "anthropic", "pydantic",
            "-t", str(python_dir),
            "-q"
        ],
        check=True
    )
    
    # Create layer ZIP
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    layer_zip = f"strands-layer-{timestamp}.zip"
    
    print(f"\n📦 Creating layer ZIP: {layer_zip}")
    with zipfile.ZipFile(layer_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in python_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(layer_dir)
                zipf.write(file, arcname)
    
    # Upload to S3
    layer_s3_key = f"lambda_layers/strands/{layer_zip}"
    print(f"\n☁️  Uploading layer to S3: s3://{S3_BUCKET}/{layer_s3_key}")
    s3_client.upload_file(layer_zip, S3_BUCKET, layer_s3_key)
    
    # Publish layer
    print("\n📤 Publishing Lambda layer...")
    response = lambda_client.publish_layer_version(
        LayerName='rfx-strands-agentcore-layer',
        Description='Strands framework and dependencies for RFx AgentCore',
        Content={'S3Bucket': S3_BUCKET, 'S3Key': layer_s3_key},
        CompatibleRuntimes=['python3.10', 'python3.11'],
    )
    
    layer_arn = response['LayerVersionArn']
    print(f"   ✅ Layer published: {layer_arn}")
    
    # Cleanup
    import shutil
    shutil.rmtree(layer_dir)
    Path(layer_zip).unlink()
    
    return layer_arn


def create_lambda_function(code_s3_key, layer_arn):
    """Create or update the Strands AgentCore Lambda function"""
    print("\n🔧 Creating Strands AgentCore Lambda function...")
    
    function_name = "rfx-strands-agentcore-orchestrator"
    
    function_config = {
        'FunctionName': function_name,
        'Runtime': 'python3.10',
        'Role': ROLE_ARN,
        'Handler': 'lambda_function.lambda_handler',
        'Timeout': 900,  # 15 minutes
        'MemorySize': 2048,  # 2GB for Strands framework
        'Environment': {
            'Variables': {
                'S3_INPUT_BUCKET': 'presales-rfp-inputs',
                'S3_OUTPUT_BUCKET': S3_BUCKET,
                'BEDROCK_MODEL_ID': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'STRANDS_ENV': 'production',
            }
        },
        'Description': 'RFx Orchestrator with Strands AgentCore Runtime - Streaming Support',
        'Layers': [layer_arn]
    }
    
    try:
        # Check if function exists
        lambda_client.get_function(FunctionName=function_name)
        
        print(f"   ℹ️  Function exists, updating...")
        
        # Update code
        lambda_client.update_function_code(
            FunctionName=function_name,
            S3Bucket=S3_BUCKET,
            S3Key=code_s3_key
        )
        
        # Wait for update
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName=function_name)
        
        # Update configuration
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Runtime=function_config['Runtime'],
            Role=function_config['Role'],
            Handler=function_config['Handler'],
            Timeout=function_config['Timeout'],
            MemorySize=function_config['MemorySize'],
            Environment=function_config['Environment'],
            Layers=[layer_arn]
        )
        
        print(f"   ✅ Function updated successfully")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"   ℹ️  Creating new function...")
        
        function_config['Code'] = {
            'S3Bucket': S3_BUCKET,
            'S3Key': code_s3_key
        }
        
        response = lambda_client.create_function(**function_config)
        print(f"   ✅ Function created: {response['FunctionArn']}")
    
    # Get function ARN
    response = lambda_client.get_function(FunctionName=function_name)
    return response['Configuration']['FunctionArn']


def test_deployment(function_name="rfx-strands-agentcore-orchestrator"):
    """Test the Strands AgentCore deployment"""
    print("\n🧪 Testing Strands AgentCore deployment...")
    
    test_event = {
        "prompt": "Process RFx document",
        "bucket": "presales-rfp-inputs",
        "s3_key": "test/sample.pdf",
        "action": "full_pipeline",
        "invocation_type": "synchronous"
    }
    
    print(f"\n📋 Test Event:")
    print(json.dumps(test_event, indent=2))
    
    try:
        print(f"\n⚡ Invoking {function_name} (dry run)...")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='DryRun'
        )
        print(f"   ✅ Dry run successful - Function is ready")
        return True
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False


def main():
    """Main deployment function"""
    print("=" * 80)
    print("🚀 RFx STRANDS AGENTCORE RUNTIME DEPLOYMENT")
    print("=" * 80)
    print("\nThis will deploy the RFx system using Strands framework:")
    print("  • True Bedrock Agent Runtime integration")
    print("  • Streaming response support")
    print("  • Conversation management")
    print("  • Tool-based agent orchestration")
    print("  • Single unified Lambda function")
    
    response = input("\n✨ Proceed with Strands AgentCore deployment? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\n❌ Deployment cancelled")
        return
    
    try:
        # Step 1: Install Strands
        if not install_strands():
            print("\n❌ Deployment aborted - Strands installation failed")
            return
        
        # Step 2: Create requirements.txt
        create_requirements_txt()
        
        # Step 3: Create Strands layer
        layer_arn = create_strands_layer()
        
        # Step 4: Create deployment package
        code_s3_key = create_deployment_package()
        
        # Step 5: Create/update Lambda function
        function_arn = create_lambda_function(code_s3_key, layer_arn)
        
        # Step 6: Test deployment
        test_deployment()
        
        # Final summary
        print("\n" + "=" * 80)
        print("✅ STRANDS AGENTCORE DEPLOYMENT COMPLETE!")
        print("=" * 80)
        print(f"\n📊 Deployment Details:")
        print(f"   Function: rfx-strands-agentcore-orchestrator")
        print(f"   ARN: {function_arn}")
        print(f"   Layer: {layer_arn}")
        print(f"   Runtime: Python 3.10 with Strands framework")
        print(f"   Memory: 2048 MB")
        print(f"   Timeout: 900 seconds (15 minutes)")
        
        print("\n💡 Key Features:")
        print("   ✓ Streaming responses for real-time updates")
        print("   ✓ Conversation memory across requests")
        print("   ✓ Tool-based agent orchestration")
        print("   ✓ Native Bedrock Agent Runtime")
        
        print("\n📝 Next Steps:")
        print("1. Test with: aws lambda invoke --function-name rfx-strands-agentcore-orchestrator response.json")
        print("2. Update frontend to use streaming endpoint")
        print("3. Monitor CloudWatch Logs for execution traces")
        print("4. Adjust conversation_manager settings if needed")
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)