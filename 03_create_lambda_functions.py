#!/usr/bin/env python3
"""
Create Lambda Functions for RFx Agents
Run in SageMaker: python 03_create_lambda_functions.py
"""

import boto3
import json
import time
import zipfile
import io
from pathlib import Path

def create_minimal_lambda_zip():
    """Create a minimal valid Lambda deployment package"""
    # Create a minimal lambda_function.py that just imports from the layer
    minimal_code = '''# Minimal Lambda function - actual code is in Layer
import sys
sys.path.insert(0, '/opt/python')
from agentcore_wrapper import lambda_handler
'''
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr('lambda_function.py', minimal_code)
    
    return zip_buffer.getvalue()


def create_lambda_functions():
    """Create all Lambda functions for RFx agents"""
    
    print("=" * 70)
    print("⚡ CREATE LAMBDA FUNCTIONS")
    print("=" * 70)
    
    # Configuration
    region = 'us-east-1'
    lambda_role = 'arn:aws:iam::040504913362:role/HCL-User-Role-Aiml-lambda'
    
    # Load layer info
    layer_info_file = Path.cwd() / "lambda_layer_info.json"
    if not layer_info_file.exists():
        print(f"\n❌ ERROR: lambda_layer_info.json not found")
        print(f"💡 Run 02_upload_and_create_layer.py first!")
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
    
    # Define Lambda functions to create
    # Note: AWS_REGION is reserved and automatically provided by Lambda
    # Handler is lambda_function.lambda_handler (imports from layer)
    lambda_functions = [
        {
            'name': 'rfx-orchestrator-function',
            'handler': 'lambda_function.lambda_handler',
            'description': 'RFx Orchestrator Agent - Full pipeline automation',
            'timeout': 900,
            'memory': 1024,
            'env_vars': {
                'S3_INPUT_BUCKET': 'presales-rfp-inputs',
                'S3_OUTPUT_BUCKET': 'presales-rfp-outputs'
            }
        },
        {
            'name': 'rfx-parsing-function',
            'handler': 'lambda_function.lambda_handler',
            'description': 'RFx Parsing Agent - Document parsing',
            'timeout': 600,
            'memory': 1024,
            'env_vars': {
                'S3_INPUT_BUCKET': 'presales-rfp-inputs',
                'S3_OUTPUT_BUCKET': 'presales-rfp-outputs',
                'AGENT_TYPE': 'parsing'
            }
        },
        {
            'name': 'rfx-clarification-function',
            'handler': 'lambda_function.lambda_handler',
            'description': 'Clarification Agent - Generate questions',
            'timeout': 600,
            'memory': 512,
            'env_vars': {
                'S3_OUTPUT_BUCKET': 'presales-rfp-outputs',
                'AGENT_TYPE': 'clarification'
            }
        },
        {
            'name': 'rfx-pricing-function',
            'handler': 'lambda_function.lambda_handler',
            'description': 'Pricing & Funding Agent - Cost estimation',
            'timeout': 600,
            'memory': 512,
            'env_vars': {
                'S3_OUTPUT_BUCKET': 'presales-rfp-outputs',
                'AGENT_TYPE': 'pricing'
            }
        },
        {
            'name': 'rfx-sow-function',
            'handler': 'lambda_function.lambda_handler',
            'description': 'SOW Drafting Agent - Create SOW documents',
            'timeout': 600,
            'memory': 512,
            'env_vars': {
                'S3_OUTPUT_BUCKET': 'presales-rfp-outputs',
                'AGENT_TYPE': 'sow'
            }
        }
    ]
    
    created_functions = []
    
    # Create each function
    for idx, func_config in enumerate(lambda_functions, 1):
        print(f"\n{'=' * 70}")
        print(f"⚡ [{idx}/{len(lambda_functions)}] Creating: {func_config['name']}")
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
                # Update existing function configuration
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
                
                # Wait for update to complete
                print(f"   ⏳ Waiting for update...")
                time.sleep(5)
                
                print(f"   ✅ Function updated successfully!")
                
            else:
                # Create new function
                response = lambda_client.create_function(
                    FunctionName=func_config['name'],
                    Runtime='python3.10',
                    Role=lambda_role,
                    Handler=func_config['handler'],
                    Description=func_config['description'],
                    Timeout=func_config['timeout'],
                    MemorySize=func_config['memory'],
                    Environment={'Variables': func_config['env_vars']},
                    Code={
                        'ZipFile': minimal_zip  # Minimal valid ZIP with layer import
                    },
                    Layers=[layer_arn],
                    Architectures=['x86_64']
                )
                
                print(f"   ✅ Function created successfully!")
                print(f"   📝 ARN: {response['FunctionArn']}")
            
            # Get function info
            func_info = lambda_client.get_function(FunctionName=func_config['name'])
            func_arn = func_info['Configuration']['FunctionArn']
            
            created_functions.append({
                'name': func_config['name'],
                'arn': func_arn,
                'handler': func_config['handler']
            })
            
            print(f"   📊 Timeout: {func_config['timeout']}s")
            print(f"   📊 Memory: {func_config['memory']}MB")
            
        except Exception as e:
            print(f"   ❌ Failed to create/update function: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Save function info
    if created_functions:
        functions_file = Path.cwd() / "lambda_functions_info.json"
        with open(functions_file, 'w') as f:
            json.dump({
                'functions': created_functions,
                'region': region,
                'layer_arn': layer_arn,
                'role_arn': lambda_role
            }, f, indent=2)
        
        print(f"\n💾 Functions info saved to: {functions_file}")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ LAMBDA FUNCTIONS CREATION COMPLETE")
    print("=" * 70)
    print(f"\n📊 Created/Updated {len(created_functions)}/{len(lambda_functions)} functions:")
    for func in created_functions:
        print(f"   ✅ {func['name']}")
    
    print(f"\n💡 Next: Run 04_configure_cognito_permissions.py")
    
    return created_functions


if __name__ == "__main__":
    try:
        functions = create_lambda_functions()
        if functions:
            print(f"\n✅ SUCCESS! Created {len(functions)} Lambda functions")
        else:
            print(f"\n⚠️  No functions were created")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

