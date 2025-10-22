### Step1: curl -LsSf https://astral.sh/uv/install.sh | sh

# AgentCore Deployment Project

This repository contains scripts and configurations to package, deploy, and test the AgentCore layer and its runtime in a cloud environment. The project also includes configuration for Cognito integration and automated deployment using buildspec and Docker.

---

## Project Structure

.
├── agentcore_package/ # Core AgentCore package files
├── Agents/ # Agents
├── generated_diagrams/ # Automatically generated diagrams
├── package/ # Deployment packages
├── 00_deploy_agentcore.py # Script to deploy AgentCore
├── 01_package_agentcore_layer.py # Script to package the AgentCore layer
├── 02_upload_agentcore_layer.py # Upload packaged layer to cloud
├── 03_create_agentcore_function.py # Create Lambda function for AgentCore
├── 04_configure_cognito_agentcore.py # Configure Cognito for AgentCore
├── 07_test_agentcore_runtime.py # Runtime tests for AgentCore
├── deploy_agentcore.ipynb # Jupyter notebook for deployment
├── deploy_to_runtime_layer.py # Deploy scripts to runtime layer
├── Dockerfile # Docker configuration
├── lambda_function.py # Example Lambda function
├── agentcore_layer_info.json # Metadata for AgentCore layer
├── lambda_layer_info.json # Metadata for Lambda layer
├── buildspec.yml # Build specification for CI/CD
└── =1.4.0 # Versioning info



---

## Requirements

- Python 3.9+
- AWS CLI configured
- Docker (for building containerized deployments)
- Required Python packages listed in `requirements.txt` (create one if not present)

---

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-folder>

2. Install dependencies:

pip install -r requirements.txt


3. Configure AWS credentials:

aws configure

## Deployment Steps

You can deploy the components step by step or automate the entire process using a single script.

### Step-by-Step Deployment

1. **Package the AgentCore Layer**  
   python 01_package_agentcore_layer.py
Packages the required dependencies and code into a Lambda layer.

2. **Upload the Layer
 python 02_upload_agentcore_layer.py
Uploads the packaged layer to AWS Lambda

3. **Create the Lambda Function**
 python 03_create_agentcore_function.py
Creates the Lambda function and attaches the uploaded layer.

## Automated Deployment

Run the following script to execute all steps in order:
 python deploy_all.py

This script automates packaging, uploading, function creation, and Cognito configuration.

## Docker Deployment

Build and run the Docker container:

docker build -t agentcore .
docker run -it agentcore

