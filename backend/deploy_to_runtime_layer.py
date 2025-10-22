import boto3
import zipfile
import os
import subprocess
import shutil

def push_lambda_agentcore():
    
    lambda_name = "bedrock-agent-pipeline"
    region = "us-east-1"
    role_arn = <lambda_role_arn>
    
    # Clean old build
    if os.path.exists("package"):
        shutil.rmtree("package")
    
    os.makedirs("package", exist_ok=True)
    
    # Step 1: Install dependencies locally
    print("📦 Installing dependencies...")
    subprocess.check_call([
        "pip", "install", "-r", "requirements.txt", "--target", "./package"
    ])
    
    # Step 2: Add lambda_function.py to the package
    shutil.copy("lambda_function.py", "./package/")
    
    # Step 3: Zip everything
    print("🧩 Creating deployment package...")
    with zipfile.ZipFile("lambda_package.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk("package"):
            for file in files:
                file_path = os.path.join(root, file)
                zf.write(file_path, os.path.relpath(file_path, "package"))
    
    # Step 4: Initialize Lambda client
    lambda_client = boto3.client("lambda", region_name=region)
    
    # Step 5: Create or update Lambda
    with open("lambda_package.zip", "rb") as f:
        zip_bytes = f.read()
    
    try:
        lambda_client.get_function(FunctionName=lambda_name)
        print("🔁 Updating existing Lambda code...")
        lambda_client.update_function_code(
            FunctionName=lambda_name, ZipFile=zip_bytes
        )
    except lambda_client.exceptions.ResourceNotFoundException:
        print("🆕 Creating new Lambda function...")
        lambda_client.create_function(
            FunctionName=lambda_name,
            Runtime="python3.9",
            Role=role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": zip_bytes},
            Timeout=300,
            MemorySize=1024,
        )
    
    print("✅ Lambda deployment complete.")
    
    # print("✅ Lambda deployment complete.")
if __name__=="__main__":
    push_lambda_agentcore()
