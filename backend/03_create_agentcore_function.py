"""
03_create_agentcore_function.py - Create/Update AgentCore Lambda Function
Handles Layer import, streaming multi-agent pipeline, and safe updates.
"""

import boto3
import json
import time
import zipfile
import io
from pathlib import Path
import botocore

# ===============================
# Helper Functions
# ===============================

def create_minimal_lambda_zip():
    """Create a minimal valid Lambda deployment package with main.py imports"""
    minimal_code = '''# AgentCore Lambda function - code is in Layer
import sys
sys.path.insert(0, '/opt/python')

# CRITICAL: Import from main.py (AgentCore)
from main import lambda_handler
'''
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr('lambda_function.py', minimal_code)
    return zip_buffer.getvalue()


def wait_for_lambda_update(lambda_client, function_name, timeout=60):
    """Wait until Lambda function update is complete"""
    elapsed = 0
    interval = 3
    while elapsed < timeout:
        response = lambda_client.get_function(FunctionName=function_name)
        status = response['Configuration'].get('State', '')
        if status == 'Active':
            return True
        print(f"   ⏳ Lambda update in progress... waiting {interval}s")
        time.sleep(interval)
        elapsed += interval
    raise TimeoutError(f"Lambda function {function_name} update did not complete in {timeout}s")


# ===============================
# Main Function
# ===============================

def create_agentcore_lambda_function():
    """Create or update the AgentCore Lambda function safely"""
    print("=" * 70)
    print("⚡ CREATE AGENTCORE LAMBDA FUNCTION")
    print("=" * 70)

    # Configuration
    region = 'us-east-1'
    lambda_role = <lambda_role_arn>
    function_name = 'rfx-agentcore-orchestrator'

    # Load layer info
    layer_info_file = Path.cwd() / "agentcore_layer_info.json"
    if not layer_info_file.exists():
        print(f"\n❌ ERROR: agentcore_layer_info.json not found")
        print("💡 Run 02_upload_agentcore_layer.py first!")
        return None

    with open(layer_info_file, 'r') as f:
        layer_info = json.load(f)
    layer_arn = layer_info['layer_arn']

    print(f"\n📝 Using Layer ARN: {layer_arn}")
    print(f"🔐 Using IAM Role: {lambda_role}")

    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name=region)

    # Create minimal deployment package
    print(f"\n📦 Creating minimal deployment package...")
    minimal_zip = create_minimal_lambda_zip()
    print(f"   ✅ Package created ({len(minimal_zip)} bytes)")

    # Function configuration
    func_config = {
        'name': function_name,
        'handler': 'lambda_function.lambda_handler',
        'description': 'RFx AgentCore Orchestrator - Streaming multi-agent pipeline',
        'timeout': 900,
        'memory': 2048,
        'env_vars': {
            'S3_INPUT_BUCKET': 'presales-rfp-inputs',
            'S3_OUTPUT_BUCKET': 'presales-rfp-outputs',
            'PYTHONPATH': '/opt/python',
        }
    }

    print(f"\n{'=' * 70}")
    print(f"⚡ Creating/Updating: {func_config['name']}")
    print(f"{'=' * 70}")

    try:
        # Check if function exists
        function_exists = False
        try:
            lambda_client.get_function(FunctionName=func_config['name'])
            function_exists = True
            print(f"   ℹ️  Function already exists, will update...")
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"   ℹ️  Creating new function...")

        if function_exists:
            # Update configuration first
            print(f"   🔄 Updating function configuration...")
            lambda_client.update_function_configuration(
                FunctionName=func_config['name'],
                Role=lambda_role,
                Handler=func_config['handler'],
                Description=func_config['description'],
                Timeout=func_config['timeout'],
                MemorySize=func_config['memory'],
                Environment={'Variables': func_config['env_vars']},
                Layers=[layer_arn]
            )
            wait_for_lambda_update(lambda_client, func_config['name'], timeout=60)

            # Update function code with retry for ResourceConflictException
            for i in range(5):
                try:
                    print(f"   🔄 Updating function code... (attempt {i+1})")
                    lambda_client.update_function_code(
                        FunctionName=func_config['name'],
                        ZipFile=minimal_zip
                    )
                    wait_for_lambda_update(lambda_client, func_config['name'], timeout=60)
                    print("   ✅ Function updated successfully!")
                    break
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceConflictException':
                        print("   ⚠️ Update in progress, retrying in 5s...")
                        time.sleep(5)
                    else:
                        raise
        else:
            # Create new function
            response = lambda_client.create_function(
                FunctionName=func_config['name'],
                Runtime='python3.11',
                Role=lambda_role,
                Handler=func_config['handler'],
                Description=func_config['description'],
                Timeout=func_config['timeout'],
                MemorySize=func_config['memory'],
                Environment={'Variables': func_config['env_vars']},
                Code={'ZipFile': minimal_zip},
                Layers=[layer_arn],
                Architectures=['x86_64']
            )
            print(f"   ✅ Function created successfully!")
            print(f"   📝 ARN: {response['FunctionArn']}")

        # Save function info
        func_info = lambda_client.get_function(FunctionName=func_config['name'])
        function_data = {
            'name': func_config['name'],
            'arn': func_info['Configuration']['FunctionArn'],
            'handler': func_config['handler'],
            'region': region,
            'layer_arn': layer_arn,
            'role_arn': lambda_role
        }

        functions_file = Path.cwd() / "agentcore_function_info.json"
        with open(functions_file, 'w') as f:
            json.dump(function_data, f, indent=2)

        print(f"\n💾 Function info saved to: {functions_file}")
        print("\n✅ AGENTCORE LAMBDA FUNCTION READY")
        return function_data

    except Exception as e:
        print(f"   ❌ Failed to create/update function: {e}")
        import traceback
        traceback.print_exc()
        return None


# ===============================
# CLI Entry Point
# ===============================
if __name__ == "__main__":
    try:
        function = create_agentcore_lambda_function()
        if function:
            print(f"\n✅ SUCCESS! AgentCore function created/updated: {function['name']}")
        else:
            print(f"\n⚠️  Function creation/update failed")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()