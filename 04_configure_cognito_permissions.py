#!/usr/bin/env python3
"""
Configure Cognito Identity Pool Permissions to invoke Lambda functions
Run in SageMaker: python 04_configure_cognito_permissions.py
"""

import boto3
import json
from pathlib import Path

def configure_cognito_permissions():
    """Add Lambda invocation permissions to Cognito Identity Pool role"""
    
    print("=" * 70)
    print("🔐 CONFIGURE COGNITO PERMISSIONS")
    print("=" * 70)
    
    # Configuration
    region = 'us-east-1'
    cognito_pool_id = 'us-east-1:896efff8-cd15-4b26-a376-189b81e902f8'
    
    # Load Lambda functions info
    functions_file = Path.cwd() / "lambda_functions_info.json"
    if not functions_file.exists():
        print(f"\n❌ ERROR: lambda_functions_info.json not found")
        print(f"💡 Run 03_create_lambda_functions.py first!")
        return None
    
    with open(functions_file, 'r') as f:
        functions_info = json.load(f)
    
    lambda_arns = [func['arn'] for func in functions_info['functions']]
    
    print(f"\n📝 Cognito Pool ID: {cognito_pool_id}")
    print(f"⚡ Lambda functions to allow: {len(lambda_arns)}")
    
    # Initialize clients
    cognito_identity = boto3.client('cognito-identity', region_name=region)
    iam = boto3.client('iam', region_name=region)
    
    # Get identity pool details
    print(f"\n🔍 STEP 1: Get Identity Pool Details")
    try:
        pool = cognito_identity.describe_identity_pool(
            IdentityPoolId=cognito_pool_id
        )
        print(f"   ✅ Found pool: {pool['IdentityPoolName']}")
        print(f"   📝 Unauthenticated access: {pool.get('AllowUnauthenticatedIdentities', False)}")
    except Exception as e:
        print(f"   ❌ Failed to get pool details: {e}")
        return None
    
    # Get roles associated with the identity pool
    print(f"\n🔍 STEP 2: Get Identity Pool Roles")
    try:
        roles = cognito_identity.get_identity_pool_roles(
            IdentityPoolId=cognito_pool_id
        )
        
        unauthenticated_role_arn = roles.get('Roles', {}).get('unauthenticated')
        authenticated_role_arn = roles.get('Roles', {}).get('authenticated')
        
        print(f"   📝 Unauthenticated Role: {unauthenticated_role_arn or 'Not set'}")
        print(f"   📝 Authenticated Role: {authenticated_role_arn or 'Not set'}")
        
        # Decide which role to update (prefer unauthenticated for testing)
        target_role_arn = unauthenticated_role_arn or authenticated_role_arn
        
        if not target_role_arn:
            print(f"   ❌ No role found for identity pool")
            return None
        
        # Extract role name from ARN
        role_name = target_role_arn.split('/')[-1]
        print(f"   ✅ Target role: {role_name}")
        
    except Exception as e:
        print(f"   ❌ Failed to get roles: {e}")
        return None
    
    # Create policy document for Lambda invocation
    print(f"\n📝 STEP 3: Create Lambda Invocation Policy")
    
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": lambda_arns
            }
        ]
    }
    
    policy_name = "RFxAgentsLambdaInvocationPolicy"
    
    print(f"   📝 Policy name: {policy_name}")
    print(f"   ⚡ Allowing invocation of {len(lambda_arns)} functions")
    
    # Attach inline policy to the role
    print(f"\n🔧 STEP 4: Attach Policy to Role")
    try:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"   ✅ Policy attached successfully!")
        
    except Exception as e:
        print(f"   ❌ Failed to attach policy: {e}")
        
        # Try to update existing policy
        print(f"   🔄 Attempting to update existing policy...")
        try:
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document)
            )
            print(f"   ✅ Policy updated successfully!")
        except Exception as e2:
            print(f"   ❌ Failed to update policy: {e2}")
            return None
    
    # Verify the policy
    print(f"\n✓ STEP 5: Verify Policy")
    try:
        policy = iam.get_role_policy(
            RoleName=role_name,
            PolicyName=policy_name
        )
        print(f"   ✅ Policy verified and active")
        
    except Exception as e:
        print(f"   ⚠️  Could not verify policy: {e}")
    
    # Save configuration
    cognito_config = {
        'identity_pool_id': cognito_pool_id,
        'role_name': role_name,
        'role_arn': target_role_arn,
        'policy_name': policy_name,
        'lambda_functions': lambda_arns
    }
    
    config_file = Path.cwd() / "cognito_config.json"
    with open(config_file, 'w') as f:
        json.dump(cognito_config, f, indent=2)
    
    print(f"\n💾 Configuration saved to: {config_file}")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ COGNITO PERMISSIONS CONFIGURED")
    print("=" * 70)
    print(f"\n📝 Identity Pool: {cognito_pool_id}")
    print(f"🔐 Role: {role_name}")
    print(f"📋 Policy: {policy_name}")
    print(f"⚡ Lambda functions allowed: {len(lambda_arns)}")
    
    print(f"\n💡 Next: Test from Cloud9 frontend")
    
    return cognito_config


if __name__ == "__main__":
    try:
        config = configure_cognito_permissions()
        if config:
            print(f"\n✅ SUCCESS! Cognito configured to invoke Lambda functions")
        else:
            print(f"\n❌ FAILED to configure Cognito permissions")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

