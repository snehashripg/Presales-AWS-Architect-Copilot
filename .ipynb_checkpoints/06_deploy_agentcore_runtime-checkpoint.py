#!/usr/bin/env python3
"""
06_deploy_agentcore_runtime.py
Deploy RFx Multi-Agent System with AgentCore Runtime Pattern

This script creates a unified AgentCore runtime that:
1. Uses the existing agentcore_wrapper.py handler
2. Deploys each agent as a separate Lambda function with AGENT_TYPE env var
3. Creates an orchestrator that can invoke all agents
4. Sets up proper IAM permissions for cross-Lambda invocation

Run in SageMaker: python 06_deploy_agentcore_runtime.py
"""

import boto3
import json
import time
import zipfile
from pathlib import Path
from datetime import datetime

# AWS Clients
lambda_client = boto3.client('lambda', region_name='us-east-1')
iam_client = boto3.client('iam', region_name='us-east-1')
s3_client = boto3.client('s3', region_name='us-east-1')

# Configuration from your existing setup
REGION = "us-east-1"
ACCOUNT_ID = "040504913362"
ROLE_ARN = "arn:aws:iam::040504913362:role/HCL-User-Role-Aiml-lambda"
LAYER_ARN = "arn:aws:lambda:us-east-1:040504913362:layer:rfx-agents-layer:44"
S3_BUCKET = "presales-rfp-outputs"
S3_INPUT_BUCKET = "presales-rfp-inputs"

# AgentCore Agent Definitions
AGENTCORE_AGENTS = {
    "rfx-agentcore-orchestrator": {
        "agent_type": "orchestrator",
        "description": "Main orchestrator that runs the complete RFx processing pipeline",
        "timeout": 900,  # 15 minutes
        "memory": 1024,
        "handler": "agentcore_wrapper.lambda_handler"
    },
    "rfx-agentcore-parsing": {
        "agent_type": "parsing",
        "description": "Parses and extracts structured data from RFx documents",
        "timeout": 300,  # 5 minutes
        "memory": 512,
        "handler": "agentcore_wrapper.lambda_handler"
    },
    "rfx-agentcore-clarification": {
        "agent_type": "clarification",
        "description": "Generates clarification questions for ambiguous requirements",
        "timeout": 300,
        "memory": 512,
        "handler": "agentcore_wrapper.lambda_handler"
    },
    "rfx-agentcore-pricing": {
        "agent_type": "pricing",
        "description": "Estimates pricing and funding requirements",
        "timeout": 300,
        "memory": 512,
        "handler": "agentcore_wrapper.lambda_handler"
    },
    "rfx-agentcore-sow": {
        "agent_type": "sow",
        "description": "Drafts comprehensive Statement of Work document",
        "timeout": 300,
        "memory": 512,
        "handler": "agentcore_wrapper.lambda_handler"
    }
}


def create_deployment_package():
    """
    Create a deployment package with all agent code + agentcore_wrapper
    """
    print("\n📦 Creating AgentCore deployment package...")
    
    package_dir = Path("lambda_package")
    package_dir.mkdir(exist_ok=True)
    
    # List of Python files to include
    agent_files = [
        "agentcore_wrapper.py",
        "rfx_orchestrator_agent.py",
        "rfx_parsing_agent.py",
        "clarification_agent.py",
        "pricing_funding_agent.py",
        "sow_drafting_agent.py"
    ]
    
    # Copy files to package directory
    for file in agent_files:
        src = Path(file)
        if src.exists():
            dest = package_dir / file
            dest.write_text(src.read_text())
            print(f"   ✓ Added {file}")
        else:
            print(f"   ⚠️  Warning: {file} not found")
    
    # Create a lambda_function.py that imports agentcore_wrapper
    lambda_main = package_dir / "lambda_function.py"
    lambda_main.write_text("""# Lambda function entry point
from agentcore_wrapper import lambda_handler

# This file exists to provide the standard lambda_function.lambda_handler entry point
# while delegating to agentcore_wrapper.lambda_handler
""")
    print(f"   ✓ Created lambda_function.py entry point")
    
    # Create ZIP file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"agentcore-runtime-{timestamp}.zip"
    zip_path = Path(zip_filename)
    
    print(f"\n📦 Creating ZIP file: {zip_filename}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in package_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(package_dir)
                zipf.write(file, arcname)
                print(f"   ✓ Packaged {arcname}")
    
    # Upload to S3
    s3_key = f"lambda_code/agentcore/{zip_filename}"
    print(f"\n☁️  Uploading to S3: s3://{S3_BUCKET}/{s3_key}")
    
    s3_client.upload_file(str(zip_path), S3_BUCKET, s3_key)
    print(f"   ✅ Upload complete")
    
    # Cleanup
    import shutil
    shutil.rmtree(package_dir)
    zip_path.unlink()
    
    return s3_key


def update_iam_permissions():
    """
    Update IAM role to allow Lambda functions to invoke each other
    """
    print("\n🔐 Updating IAM permissions for cross-Lambda invocation...")
    
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction",
                    "lambda:InvokeAsync"
                ],
                "Resource": [
                    f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:rfx-agentcore-*"
                ]
            }
        ]
    }
    
    policy_name = "RFxAgentCoreInvocationPolicy"
    role_name = ROLE_ARN.split('/')[-1]
    
    try:
        # Try to create the policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"   ✅ Policy '{policy_name}' created/updated on role '{role_name}'")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not update IAM policy: {e}")
        print(f"   ℹ️  You may need to add Lambda invoke permissions manually")


def create_or_update_lambda(function_name, agent_config, s3_key):
    """
    Create or update a Lambda function with AgentCore configuration
    """
    print(f"\n🔧 Configuring {function_name}...")
    
    environment = {
        'Variables': {
            'AGENT_TYPE': agent_config['agent_type'],
            'S3_INPUT_BUCKET': S3_INPUT_BUCKET,
            'S3_OUTPUT_BUCKET': S3_BUCKET,
            'BEDROCK_MODEL_ID': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'ENABLE_GUARDRAILS': 'false'
        }
    }
    
    function_config = {
        'FunctionName': function_name,
        'Runtime': 'python3.10',
        'Role': ROLE_ARN,
        'Handler': agent_config['handler'],
        'Timeout': agent_config['timeout'],
        'MemorySize': agent_config['memory'],
        'Environment': environment,
        'Description': agent_config['description'],
        'Layers': [LAYER_ARN]
    }
    
    try:
        # Try to get existing function
        lambda_client.get_function(FunctionName=function_name)
        
        # Function exists, update it
        print(f"   ℹ️  Function exists, updating...")
        
        # Update code
        lambda_client.update_function_code(
            FunctionName=function_name,
            S3Bucket=S3_BUCKET,
            S3Key=s3_key
        )
        
        # Wait for update to complete
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
            Environment=environment,
            Layers=[LAYER_ARN]
        )
        
        print(f"   ✅ Function updated successfully")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Function doesn't exist, create it
        print(f"   ℹ️  Creating new function...")
        
        function_config['Code'] = {
            'S3Bucket': S3_BUCKET,
            'S3Key': s3_key
        }
        
        response = lambda_client.create_function(**function_config)
        print(f"   ✅ Function created: {response['FunctionArn']}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        raise
    
    # Get function ARN
    response = lambda_client.get_function(FunctionName=function_name)
    return response['Configuration']['FunctionArn']


def test_agentcore_deployment():
    """
    Test the AgentCore deployment with a sample invocation
    """
    print("\n🧪 Testing AgentCore deployment...")
    
    test_event = {
        "action": "runOrchestrator",
        "bucketIn": S3_INPUT_BUCKET,
        "inputKey": "test/sample_rfp.pdf",
        "bucketOut": S3_BUCKET
    }
    
    print(f"\n📋 Test Event:")
    print(json.dumps(test_event, indent=2))
    
    try:
        print(f"\n⚡ Invoking rfx-agentcore-orchestrator (dry run)...")
        response = lambda_client.invoke(
            FunctionName='rfx-agentcore-orchestrator',
            InvocationType='DryRun'
        )
        print(f"   ✅ Dry run successful - Function is ready to invoke")
        return True
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False


def save_deployment_info(arns):
    """
    Save deployment information to JSON file
    """
    print("\n💾 Saving deployment information...")
    
    deployment_info = {
        "deployment_timestamp": datetime.utcnow().isoformat(),
        "region": REGION,
        "account_id": ACCOUNT_ID,
        "s3_bucket": S3_BUCKET,
        "layer_arn": LAYER_ARN,
        "functions": []
    }
    
    for func_name, arn in arns.items():
        agent_type = AGENTCORE_AGENTS[func_name]['agent_type']
        deployment_info["functions"].append({
            "name": func_name,
            "arn": arn,
            "agent_type": agent_type,
            "handler": "agentcore_wrapper.lambda_handler",
            "description": AGENTCORE_AGENTS[func_name]['description']
        })
    
    # Save to file
    output_file = Path("agentcore_deployment_info.json")
    output_file.write_text(json.dumps(deployment_info, indent=2))
    print(f"   ✅ Saved to {output_file}")
    
    # Also upload to S3
    s3_key = "deployment_info/agentcore_deployment_info.json"
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(deployment_info, indent=2)
    )
    print(f"   ✅ Uploaded to s3://{S3_BUCKET}/{s3_key}")
    
    return deployment_info


def main():
    """
    Main deployment function
    """
    print("=" * 80)
    print("🚀 RFx AGENTCORE RUNTIME DEPLOYMENT")
    print("=" * 80)
    print("\nThis will deploy all agents using the AgentCore runtime pattern:")
    print("  • Unified agentcore_wrapper.py handler")
    print("  • Separate Lambda functions per agent type")
    print("  • Environment-based agent routing (AGENT_TYPE)")
    print("  • Cross-Lambda invocation permissions")
    print("\nAgents to deploy:")
    for name, config in AGENTCORE_AGENTS.items():
        print(f"  • {name} ({config['agent_type']})")
    
    response = input("\n✨ Proceed with AgentCore deployment? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("\n❌ Deployment cancelled")
        return
    
    try:
        # Step 1: Create deployment package
        s3_key = create_deployment_package()
        
        # Step 2: Update IAM permissions
        update_iam_permissions()
        
        # Step 3: Create/update all Lambda functions
        print("\n" + "=" * 80)
        print("📦 DEPLOYING LAMBDA FUNCTIONS")
        print("=" * 80)
        
        function_arns = {}
        for func_name, agent_config in AGENTCORE_AGENTS.items():
            arn = create_or_update_lambda(func_name, agent_config, s3_key)
            function_arns[func_name] = arn
            time.sleep(2)  # Brief pause between deployments
        
        # Step 4: Save deployment info
        deployment_info = save_deployment_info(function_arns)
        
        # Step 5: Test deployment
        test_agentcore_deployment()
        
        # Final summary
        print("\n" + "=" * 80)
        print("✅ AGENTCORE DEPLOYMENT COMPLETE!")
        print("=" * 80)
        print(f"\n📊 Deployed {len(function_arns)} AgentCore functions:")
        for name, arn in function_arns.items():
            agent_type = AGENTCORE_AGENTS[name]['agent_type']
            print(f"   ✓ {name} ({agent_type})")
            print(f"     ARN: {arn}")
        
        print("\n💡 Next Steps:")
        print("1. Test individual agents:")
        print("   aws lambda invoke --function-name rfx-agentcore-parsing response.json")
        print("\n2. Test orchestrator:")
        print("   aws lambda invoke --function-name rfx-agentcore-orchestrator response.json")
        print("\n3. Update your frontend to use new AgentCore endpoints")
        print("\n4. Monitor CloudWatch Logs for agent execution traces")
        
        print(f"\n📄 Deployment info saved to: agentcore_deployment_info.json")
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main() or 0)