
# #!/usr/bin/env python3
# """
# AWS Architecture Agent - Complete Integration
# - Searches Knowledge Base (text annotations with image URIs) - MAY BE EMPTY
# - Searches MCP Server (AWS Reference Architectures) - ALWAYS AVAILABLE
# - Compares results and selects best template
# - Generates custom architecture

# Knowledge Base can be empty initially - populated only after SOW approval.
# Agent handles empty KB gracefully and relies on MCP Server.
# """

# import boto3
# import json
# import base64
# from typing import Dict, List, Optional
# from datetime import datetime
# from pathlib import Path
# from mcp import StdioServerParameters, stdio_client
# from strands import Agent, tool
# from strands.models import BedrockModel
# from strands.tools.mcp import MCPClient

# class AWSArchitectureAgent:
#     def __init__(self, region: str = "us-east-1", kb_id: Optional[str] = None):
#         self.region = region
#         self.kb_id = kb_id or "WU6IC1ZQJH"
#         self.s3 = boto3.client("s3", region_name=region)

#         # === Initialize Bedrock model ===
#         self.bedrock_model = BedrockModel(
#             model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
#             region_name=region,
#             temperature=0.4,
#         )

#         # === Initialize MCP Clients (non-blocking init) ===
#         self.aws_docs_client = None
#         self.aws_diag_client = None
#         self.mcp_ready = False

#         if MCP_AVAILABLE:
#             self._initialize_mcp_clients()

#     def _initialize_mcp_clients(self):
#         """Start MCP clients immediately, keeping them persistent for reuse."""
#         try:
#             print("[MCP] 🚀 Initializing MCP servers...")

#             self.aws_docs_client = MCPClient(
#                 lambda: stdio_client(
#                     StdioServerParameters(
#                         command="uvx",
#                         args=["awslabs.aws-documentation-mcp-server@latest"]
#                     )
#                 )
#             )
#             self.aws_diag_client = MCPClient(
#                 lambda: stdio_client(
#                     StdioServerParameters(
#                         command="uvx",
#                         args=["awslabs.aws-diagram-mcp-server@latest"]
#                     )
#                 )
#             )

#             # Explicitly initialize synchronously
#             self.aws_docs_client.initialize_sync()
#             self.aws_diag_client.initialize_sync()
#             self.mcp_ready = True

#             print("[MCP] ✅ MCP clients initialized successfully.")
#         except Exception as e:
#             print(f"[MCP] ⚠️ MCP initialization failed: {e}")
#             self.mcp_ready = False

# class AWSArchitectureAgent:
#     """
#     AWS Architecture Generation Agent
#     - KB Tool: Searches text annotations (with image URIs) - handles empty KB
#     - MCP Tools: AWS docs and diagrams - primary source
#     - Agent orchestrates and generates custom architecture
#     """
    
#     def __init__(self, region: str = "us-east-1", kb_id: Optional[str] = None):
#         self.region = region
#         self.kb_id = "WU6IC1ZQJH"
#         self.s3 = boto3.client("s3", region_name=region)
#         self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        
#         # Initialize MCP Clients
#         self.aws_docs_client = MCPClient(
#             lambda: stdio_client(
#                 StdioServerParameters(
#                     command="uvx", 
#                     args=["awslabs.aws-documentation-mcp-server@latest"]
#                 )
#             )
#         )
        
#         self.aws_diag_client = MCPClient(
#             lambda: stdio_client(
#                 StdioServerParameters(
#                     command="uvx", 
#                     args=["awslabs.aws-diagram-mcp-server@latest"]
#                 )
#             )
#         )
        
#         # Bedrock Model
#         self.bedrock_model = BedrockModel(
#             model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
#             region_name=region,
#             temperature=0.4,
#         )
        
#         self.agent = None
    
#     # ============================================
#     # Knowledge Base Tool (Handles Empty KB)
#     # ============================================
    
#     def _create_kb_tool(self):
#         """Create KB search tool - gracefully handles empty KB"""
#         kb_id = self.kb_id
#         region = self.region
#         s3_client = self.s3
        
#         # Helper functions (outside the tool)
#         def extract_image_uri(content: str) -> Optional[str]:
#             """Extract image S3 URI from annotation content"""
#             import re
#             match = re.search(r'IMAGE_URI:\s*(s3://[^\s\n]+)', content)
#             if match:
#                 return match.group(1)
#             match = re.search(r'REFERENCE_IMAGE:\s*(s3://[^\s\n]+)', content)
#             if match:
#                 return match.group(1)
#             return None
        
#         def extract_title(content: str) -> Optional[str]:
#             """Extract title from annotation"""
#             import re
#             match = re.search(r'Title:\s*([^\n]+)', content)
#             if match:
#                 return match.group(1).strip()
#             return None
        
#         # Now create the actual tool
#         @tool
#         def search_knowledge_base_diagrams(query: str) -> str:
#             """
#             Search Knowledge Base for approved architecture diagrams.
            
#             NOTE: KB may be EMPTY initially - only populated after SOW approval.
#             This tool handles empty KB gracefully.
            
#             Args:
#                 query: Technical requirements or architecture description
            
#             Returns:
#                 JSON with diagrams found (includes image URIs) or empty result
#             """
#             if not kb_id:
#                 return json.dumps({
#                     "status": "skipped",
#                     "message": "Knowledge Base not configured",
#                     "results": [],
#                     "note": "Using only MCP Server for this query"
#                 })
            
#             try:
#                 bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=region)
                
#                 print(f"[KB-TOOL] 🔍 Searching Knowledge Base...")
                
#                 response = bedrock_agent.retrieve(
#                     knowledgeBaseId=kb_id,
#                     retrievalQuery={'text': query},
#                     retrievalConfiguration={
#                         'vectorSearchConfiguration': {
#                             'numberOfResults': 5
#                         }
#                     }
#                 )
                
#                 results = []
#                 for item in response.get('retrievalResults', []):
#                     content = item.get('content', {}).get('text', '')
#                     score = item.get('score', 0)
                    
#                     # Extract image URI from annotation content
#                     image_uri = extract_image_uri(content)
                    
#                     if image_uri:
#                         # Extract title from annotation
#                         title = extract_title(content)
                        
#                         results.append({
#                             'source': 'knowledge_base',
#                             'title': title or 'Company Architecture',
#                             'description': content[:300],
#                             'image_uri': image_uri,
#                             'relevance_score': score,
#                             'has_diagram': True,
#                             'type': 'approved_architecture'
#                         })
                
#                 if results:
#                     print(f"[KB-TOOL] ✅ Found {len(results)} approved diagrams")
#                 else:
#                     print(f"[KB-TOOL] ℹ️  No diagrams in KB yet (empty or no matches)")
                
#                 return json.dumps({
#                     "status": "success",
#                     "source": "knowledge_base",
#                     "results_count": len(results),
#                     "results": results[:3],
#                     "note": "KB may be empty - populated after SOW approval"
#                 }, indent=2)
                
#             except Exception as e:
#                 print(f"[KB-TOOL] ⚠️  KB search failed: {e}")
#                 return json.dumps({
#                     "status": "error",
#                     "source": "knowledge_base",
#                     "error": str(e),
#                     "results": [],
#                     "note": "Falling back to MCP Server only"
#                 })
        
#         return search_knowledge_base_diagrams
    
#     # ============================================
#     # Create Agent with All Tools
#     # ============================================
    
#     def create_agent(self):
#         """Create agent with KB + MCP tools"""
        
#         system_prompt = """You are an expert AWS Solutions Architect specializing in reference architecture selection and design.

# **Your Tools:**

# 1. **search_knowledge_base_diagrams(query)** - Search company's approved architectures
#    - Returns: Previously approved architecture diagrams with image URIs
#    - IMPORTANT: KB may be EMPTY initially - only populated after SOW approval
#    - If empty, this is NORMAL - proceed with MCP tools only

# 2. **MCP Server Tools** - AWS Reference Architectures (ALWAYS AVAILABLE)
#    - Official AWS reference architectures
#    - AWS service documentation
#    - Always use these as primary source if KB is empty

# **Workflow:**

# STEP 1: DUAL SEARCH (KB may be empty - that's OK!)
# - Call search_knowledge_base_diagrams(requirements)
#   * If results found: Great! Use approved company patterns
#   * If empty/error: NORMAL - KB populated only after approval
# - Call MCP tools to search AWS reference architectures
#   * This is PRIMARY source when KB is empty
# - Collect at least 1 diagram from available sources

# STEP 2: SELECT BEST TEMPLATE
# - If KB has results: Consider company-approved patterns first
# - If KB empty: Use MCP reference architectures (this is expected)
# - Score each available template (0-10) for similarity

# STEP 3: GENERATE CUSTOM ARCHITECTURE
# - Use selected template as foundation
# - Adapt to specific requirements
# - Follow AWS Well-Architected Framework
# - Return detailed architecture specification

# **CRITICAL:**
# - Empty KB is NORMAL - don't report as error
# - Always have MCP as fallback
# - Prefer company KB patterns when available
# - Use MCP patterns when KB is empty or no matches

# Return analysis as JSON:
# {
#     "search_results": {
#         "kb_diagrams": [...],  // May be empty
#         "mcp_diagrams": [...]   // Primary source
#     },
#     "selected_template": {
#         "source": "knowledge_base or mcp_server",
#         "title": "...",
#         "reasoning": "..."
#     },
#     "custom_architecture": {
#         "name": "...",
#         "aws_services": [...],
#         "architecture": {...}
#     }
# }
# """
        
#         # Start MCP client sessions first
#         print(f"[AGENT] 🔌 Starting MCP client sessions...")
#         try:
#             # Initialize MCP clients synchronously
#             self.aws_docs_client.initialize_sync()
#             self.aws_diag_client.initialize_sync()
#             print(f"[AGENT] ✅ MCP clients initialized")
#         except Exception as e:
#             print(f"[AGENT] ⚠️  MCP initialization warning: {e}")
#             print(f"[AGENT] ℹ️  Will use KB tool only")
        
#         # Collect all tools
#         kb_tool = self._create_kb_tool()
        
#         # Try to get MCP tools (may fail if MCP not available)
#         try:
            
#             mcp_tools = (
#                 self.aws_diag_client.list_tools_sync() +
#                 self.aws_docs_client.list_tools_sync()
#             )
#             all_tools = [kb_tool] + mcp_tools
#             print(f"[AGENT] 🔧 Initialized with {len(all_tools)} tools")
#             print(f"[AGENT]   - KB Tool: 1")
#             print(f"[AGENT]   - MCP Tools: {len(mcp_tools)}")
#         except Exception as e:
#             print(f"[AGENT] ⚠️  MCP tools unavailable: {e}")
#             print(f"[AGENT] ℹ️  Using KB tool only")
#             all_tools = [kb_tool]
        
#         self.agent = Agent(
#             model=self.bedrock_model,
#             system_prompt=system_prompt,
#             tools=all_tools
#         )
        
#         return self.agent
    
#     def __del__(self):
#         """Cleanup MCP clients on deletion"""
#         try:
#             if hasattr(self, 'aws_docs_client'):
#                 self.aws_docs_client.close_sync()
#             if hasattr(self, 'aws_diag_client'):
#                 self.aws_diag_client.close_sync()
#         except:
#             pass  # Ignore cleanup errors
    
#     # ============================================
#     # Main Execution
#     # ============================================
    
#     def run(
#         self, 
#         technical_requirements: str,parsed_key:str,
#         output_bucket: Optional[str] = None
#     ) -> Dict:
#         """
#         Generate AWS architecture from requirements
        
#         Args:
#             technical_requirements: Technical requirements from RFx
#             output_bucket: S3 bucket to save results
        
#         Returns:
#             Architecture with selected template and generation details
#         """
#         print(f"\n{'='*70}")
#         print(f"🏗️ AWS ARCHITECTURE GENERATION")
#         print(f"{'='*70}")
#         print(f"📋 Requirements: {technical_requirements[:100]}...")
#         print(f"🗄️  KB ID: {self.kb_id or 'Not configured (will use MCP only)'}")
        
#         try:
#             # Create agent
#             if not self.agent:
#                 self.create_agent()
            
#             # Build prompt
#             prompt = f"""Generate AWS reference architecture for these requirements:

# {technical_requirements}

# Workflow:
# 1. Search KB for approved architectures (may be empty - that's OK)
# 2. Search AWS Reference Architectures via MCP
# 3. Compare available diagrams, select BEST template
# 4. Generate custom architecture based on selected template

# Provide complete analysis in JSON format."""

#             print(f"\n[AGENT] 🚀 Generating architecture...")
            
#             # Run agent
#             response = self.agent(prompt)
            
#             # Parse response
#             result = self._parse_response(response)
            
#             # Add metadata
#             result['metadata'] = {
#                 'timestamp': datetime.utcnow().isoformat(),
#                 'kb_configured': bool(self.kb_id),
#                 'requirements': technical_requirements,
#                 'status': 'success'
#             }
            
#             # Save to S3
#             if output_bucket:
#                 s3_path = self._save_to_s3(result,parsed_key,output_bucket)
#                 result['s3_path'] = s3_path
            
#             print(f"\n[AGENT] ✅ Architecture generated!")
#             print(f"{'='*70}\n")
            
#             return result
            
#         except Exception as e:
#             print(f"[AGENT] ❌ Error: {e}")
#             import traceback
#             traceback.print_exc()
            
#             return {
#                 'status': 'error',
#                 'error': str(e),
#                 'traceback': traceback.format_exc()
#             }
    
#     def _parse_response(self, response) -> Dict:
#         """Parse agent response"""
#         response_text = str(response)
        
#         import re
#         json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
#         if json_match:
#             try:
#                 return {
#                     'status': 'success',
#                     'architecture': json.loads(json_match.group(0)),
#                     'raw_response': response_text[:500]
#                 }
#             except:
#                 pass
        
#         return {
#             'status': 'success',
#             'architecture': {'raw_response': response_text},
#             'note': 'Could not parse JSON'
#         }
    
#     def _save_to_s3(self, result: Dict, parsed_key: str, bucket: str) -> str:
#         """Save to S3"""
#         try:
            
#              # --- STEP 5: Store final architecture output ---
#             user_prefix = parsed_key.split("/")[0]
#             timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
#             out_folder = f"{user_prefix}/aws_architectures/"
#             out_key = f"{out_folder}{os.path.basename(parsed_key).replace('.json','')}_diagram_{ts}.json"

#             s3.put_object(
#                 Bucket=bucket,
#                 Key=out_key,
#                 Body=json.dumps(result, indent=2).encode("utf-8"),
#                 ContentType="application/json"
#             )
            
#             s3_path = f"s3://{bucket}/{out_key}"
#             print(f"[S3] 💾 Saved: {s3_path}")
#             return s3_path
#         except Exception as e:
#             print(f"[S3] ⚠️  Save failed: {e}")
#             return None


# # ============================================
# # Tool for RFx Integration
# # ============================================

# def create_aws_architecture_tool(kb_id: Optional[str] = None, region: str = "us-east-1"):
#     """
#     Factory to create AWS architecture tool for main.py integration
    
#     Args:
#         kb_id: Knowledge Base ID (optional - can be empty)
#         region: AWS region
    
#     Returns:
#         Strands tool for RFx pipeline
#     """
    
#     @tool
#     def aws_architecture_tool(technical_requirements: str) -> str:
#         """
#         Generate AWS architecture from technical requirements.
#         Searches both Knowledge Base (may be empty) and MCP Server.
        
#         Args:
#             technical_requirements: Technical requirements from parsed RFx
        
#         Returns:
#             JSON with selected template and generated architecture
#         """
#         try:
#             print(f"[AWS-ARCH-TOOL] 🏗️ Starting architecture generation...")
            
#             agent = AWSArchitectureAgent(region=region, kb_id=kb_id)
            
#             result = agent.run(
#                 technical_requirements=technical_requirements,
#                 output_bucket="presales-rfp-outputs"
#             )
            
#             return json.dumps(result, indent=2)
            
#         except Exception as e:
#             print(f"[AWS-ARCH-TOOL] ❌ Error: {e}")
#             return json.dumps({
#                 'status': 'error',
#                 'error': str(e)
#             })
    
#     return aws_architecture_tool


# # ============================================
# # Standalone Testing
# # ============================================

# if __name__ == "__main__":
#     import sys
    
#     # Configuration
#     KB_ID = "WU6IC1ZQJH"  # Set your KB ID or leave None
#     REGION = "us-east-1"
    
   
#     # # Test requirements
#     # test_requirements = """
#     # Build a serverless e-commerce platform with:
#     # - Product catalog in DynamoDB
#     # - Product images in S3
#     # - Lambda for REST API
#     # - CloudFront for CDN
#     # - Cognito for authentication
#     # - API Gateway for REST endpoints
#     # - Step Functions for order workflow
#     # - SNS for notifications
#     # """

#     parsed_key = "ravi/parsed_outputs/RFP_5_20251017_030359_parsed.json"
#     clarification_key = "ravi/clarifications/RFP_5_20251017_030359_parsed_clarifications_20251017_030413.json"
#     bucket_name = "presales-rfp-outputs"
#     output_prefix = "ravi/architecture"
    
#     s3 = boto3.client("s3", region_name=REGION)

#     # --- STEP 1: Load parsed requirements ---
#     print(f"[INFO] Loading parsed requirements from s3://{bucket_name}/{parsed_key}")
#     parsed_obj = s3.get_object(Bucket=bucket_name, Key=parsed_key)
#     parsed_data = json.loads(parsed_obj["Body"].read().decode("utf-8"))
    
#     # --- STEP 2: Load clarifications ---
#     print(f"[INFO] Loading clarifications from s3://{bucket_name}/{clarification_key}")
#     clar_obj = s3.get_object(Bucket=bucket_name, Key=clarification_key)
#     clar_data = json.loads(clar_obj["Body"].read().decode("utf-8"))
    
#     # --- STEP 3: Combine both into a single requirement prompt ---
#     combined_requirements = "### RFP Requirements:\n"
#     combined_requirements += json.dumps(parsed_data, indent=2)
#     combined_requirements += "\n\n### Clarifications:\n"
#     combined_requirements += json.dumps(clar_data, indent=2)
    
#     print(f"[INFO] Combined RFP and Clarifications loaded successfully.")
    
#     print(f"Testing with KB ID: {KB_ID or 'None (MCP only)'}")
    
#     # Create and run agent
#     agent = AWSArchitectureAgent(region=REGION, kb_id=KB_ID)
#     result = agent.run(
#         technical_requirements=combined_requirements,parsed_key=parsed_key,
#         output_bucket="presales-rfp-outputs"
#     )
    
#     # Print result
#     print("\n" + "="*70)
#     print("📊 RESULT")
#     print("="*70)
#     print(json.dumps(result, indent=2))


# #!/usr/bin/env python3
# """
# AWS Architecture Agent - Complete Integration
# - Searches Knowledge Base (text annotations with image URIs) - MAY BE EMPTY
# - Searches MCP Server (AWS Reference Architectures) - ALWAYS AVAILABLE
# - Compares results and selects best template
# - Generates custom architecture

# Knowledge Base can be empty initially - populated only after SOW approval.
# Agent handles empty KB gracefully and relies on MCP Server.
# """

# import boto3
# import json
# import os
# from typing import Dict, List, Optional
# from datetime import datetime
# from pathlib import Path
# from mcp import StdioServerParameters
# from mcp.client.stdio import stdio_client
# from strands import Agent, tool
# from strands.models import BedrockModel
# from strands.tools.mcp import MCPClient

# class AWSArchitectureAgent:
#     """
#     AWS Architecture Generation Agent
#     - KB Tool: Searches text annotations (with image URIs) - handles empty KB
#     - MCP Tools: AWS docs and diagrams - primary source
#     - Agent orchestrates and generates custom architecture
#     """
    
#     def __init__(self, region: str = "us-east-1", kb_id: Optional[str] = None):
#         self.region = region
#         self.kb_id = kb_id or "WU6IC1ZQJH"
#         self.s3 = boto3.client("s3", region_name=region)
#         self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        
#         # Initialize MCP Clients - will be started in context manager
#         self.aws_docs_client = MCPClient(
#             lambda: stdio_client(
#                 StdioServerParameters(
#                     command="uvx", 
#                     args=["awslabs.aws-documentation-mcp-server@latest"]
#                 )
#             )
#         )
        
#         self.aws_diag_client = MCPClient(
#             lambda: stdio_client(
#                 StdioServerParameters(
#                     command="uvx", 
#                     args=["awslabs.aws-diagram-mcp-server@latest"]
#                 )
#             )
#         )
        
#         # Bedrock Model
#         self.bedrock_model = BedrockModel(
#             model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
#             region_name=region,
#             temperature=0.4,
#         )
        
#         self.agent = None
    
#     # ============================================
#     # Knowledge Base Tool (Handles Empty KB)
#     # ============================================
    
#     def _create_kb_tool(self):
#         """Create KB search tool - gracefully handles empty KB"""
#         kb_id = self.kb_id
#         region = self.region
#         s3_client = self.s3
        
#         # Helper functions (outside the tool)
#         def extract_image_uri(content: str) -> Optional[str]:
#             """Extract image S3 URI from annotation content"""
#             import re
#             match = re.search(r'IMAGE_URI:\s*(s3://[^\s\n]+)', content)
#             if match:
#                 return match.group(1)
#             match = re.search(r'REFERENCE_IMAGE:\s*(s3://[^\s\n]+)', content)
#             if match:
#                 return match.group(1)
#             return None
        
#         def extract_title(content: str) -> Optional[str]:
#             """Extract title from annotation"""
#             import re
#             match = re.search(r'Title:\s*([^\n]+)', content)
#             if match:
#                 return match.group(1).strip()
#             return None
        
#         # Now create the actual tool
#         @tool
#         def search_knowledge_base_diagrams(query: str) -> str:
#             """
#             Search Knowledge Base for approved architecture diagrams.
            
#             NOTE: KB may be EMPTY initially - only populated after SOW approval.
#             This tool handles empty KB gracefully.
            
#             Args:
#                 query: Technical requirements or architecture description
            
#             Returns:
#                 JSON with diagrams found (includes image URIs) or empty result
#             """
#             if not kb_id:
#                 return json.dumps({
#                     "status": "skipped",
#                     "message": "Knowledge Base not configured",
#                     "results": [],
#                     "note": "Using only MCP Server for this query"
#                 })
            
#             try:
#                 bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=region)
                
#                 print(f"[KB-TOOL] 🔍 Searching Knowledge Base...")
                
#                 response = bedrock_agent.retrieve(
#                     knowledgeBaseId=kb_id,
#                     retrievalQuery={'text': query},
#                     retrievalConfiguration={
#                         'vectorSearchConfiguration': {
#                             'numberOfResults': 5
#                         }
#                     }
#                 )
                
#                 results = []
#                 for item in response.get('retrievalResults', []):
#                     content = item.get('content', {}).get('text', '')
#                     score = item.get('score', 0)
                    
#                     # Extract image URI from annotation content
#                     image_uri = extract_image_uri(content)
                    
#                     if image_uri:
#                         # Extract title from annotation
#                         title = extract_title(content)
                        
#                         results.append({
#                             'source': 'knowledge_base',
#                             'title': title or 'Company Architecture',
#                             'description': content[:300],
#                             'image_uri': image_uri,
#                             'relevance_score': score,
#                             'has_diagram': True,
#                             'type': 'approved_architecture'
#                         })
                
#                 if results:
#                     print(f"[KB-TOOL] ✅ Found {len(results)} approved diagrams")
#                 else:
#                     print(f"[KB-TOOL] ℹ️  No diagrams in KB yet (empty or no matches)")
                
#                 return json.dumps({
#                     "status": "success",
#                     "source": "knowledge_base",
#                     "results_count": len(results),
#                     "results": results[:3],
#                     "note": "KB may be empty - populated after SOW approval"
#                 }, indent=2)
                
#             except Exception as e:
#                 print(f"[KB-TOOL] ⚠️  KB search failed: {e}")
#                 return json.dumps({
#                     "status": "error",
#                     "source": "knowledge_base",
#                     "error": str(e),
#                     "results": [],
#                     "note": "Falling back to MCP Server only"
#                 })
        
#         return search_knowledge_base_diagrams
    
#     # ============================================
#     # Create Agent with All Tools
#     # ============================================
    
#     def create_agent(self):
#         """Create agent with KB + MCP tools"""
        
#         system_prompt = """You are an expert AWS Solutions Architect specializing in reference architecture selection and design.

# **Your Tools:**

# 1. **search_knowledge_base_diagrams(query)** - Search company's approved architectures
#    - Returns: Previously approved architecture diagrams with image URIs
#    - IMPORTANT: KB may be EMPTY initially - only populated after SOW approval
#    - If empty, this is NORMAL - proceed with MCP tools only

# 2. **MCP Server Tools** - AWS Reference Architectures (ALWAYS AVAILABLE)
#    - Official AWS reference architectures
#    - AWS service documentation
#    - Always use these as primary source if KB is empty

# **Workflow:**

# STEP 1: DUAL SEARCH (KB may be empty - that's OK!)
# - Call search_knowledge_base_diagrams(requirements)
#   * If results found: Great! Use approved company patterns
#   * If empty/error: NORMAL - KB populated only after approval
# - Call MCP tools to search AWS reference architectures
#   * This is PRIMARY source when KB is empty
# - Collect at least 1 diagram from available sources

# STEP 2: SELECT BEST TEMPLATE
# - If KB has results: Consider company-approved patterns first
# - If KB empty: Use MCP reference architectures (this is expected)
# - Score each available template (0-10) for similarity

# STEP 3: GENERATE CUSTOM ARCHITECTURE
# - Use selected template as foundation
# - Adapt to specific requirements
# - Follow AWS Well-Architected Framework
# - Return detailed architecture specification

# **CRITICAL:**
# - Empty KB is NORMAL - don't report as error
# - Always have MCP as fallback
# - Prefer company KB patterns when available
# - Use MCP patterns when KB is empty or no matches

# Return analysis as JSON:
# {
#     "search_results": {
#         "kb_diagrams": [...],  // May be empty
#         "mcp_diagrams": [...]   // Primary source
#     },
#     "selected_template": {
#         "source": "knowledge_base or mcp_server",
#         "title": "...",
#         "reasoning": "..."
#     },
#     "custom_architecture": {
#         "name": "...",
#         "aws_services": [...],
#         "architecture": {...}
#     }
# }
# """
        
#         # Collect KB tool
#         kb_tool = self._create_kb_tool()
        
#         # Get MCP tools - must be done inside Agent context
#         try:
#             print(f"[AGENT] 🔧 Collecting MCP tools...")
#             mcp_tools = (
#                 list(self.aws_diag_client.list_tools()) +
#                 list(self.aws_docs_client.list_tools())
#             )
#             all_tools = [kb_tool] + mcp_tools
#             print(f"[AGENT] ✅ Initialized with {len(all_tools)} tools")
#             print(f"[AGENT]   - KB Tool: 1")
#             print(f"[AGENT]   - MCP Tools: {len(mcp_tools)}")
#         except Exception as e:
#             print(f"[AGENT] ⚠️  MCP tools unavailable: {e}")
#             print(f"[AGENT] ℹ️  Using KB tool only")
#             all_tools = [kb_tool]
        
#         self.agent = Agent(
#             model=self.bedrock_model,
#             system_prompt=system_prompt,
#             tools=all_tools
#         )
        
#         return self.agent
    
#     # ============================================
#     # Main Execution
#     # ============================================
    
#     def run(
#         self, 
#         technical_requirements: str,
#         parsed_key: str,
#         output_bucket: Optional[str] = None
#     ) -> Dict:
#         """
#         Generate AWS architecture from requirements
        
#         Args:
#             technical_requirements: Technical requirements from RFx
#             parsed_key: S3 key for the parsed file
#             output_bucket: S3 bucket to save results
        
#         Returns:
#             Architecture with selected template and generation details
#         """
#         print(f"\n{'='*70}")
#         print(f"🏗️ AWS ARCHITECTURE GENERATION")
#         print(f"{'='*70}")
#         print(f"📋 Requirements: {technical_requirements[:100]}...")
#         print(f"🗄️  KB ID: {self.kb_id or 'Not configured (will use MCP only)'}")
        
#         try:
#             # Create agent (must be inside MCP context)
#             if not self.agent:
#                 self.create_agent()
            
#             # Build prompt
#             prompt = f"""Generate AWS reference architecture for these requirements:

# {technical_requirements}

# Workflow:
# 1. Search KB for approved architectures (may be empty - that's OK)
# 2. Search AWS Reference Architectures via MCP
# 3. Compare available diagrams, select BEST template
# 4. Generate custom architecture based on selected template

# Provide complete analysis in JSON format."""

#             print(f"\n[AGENT] 🚀 Generating architecture...")
            
#             # Run agent
#             response = self.agent(prompt)
            
#             # Parse response
#             result = self._parse_response(response)
            
#             # Add metadata
#             result['metadata'] = {
#                 'timestamp': datetime.utcnow().isoformat(),
#                 'kb_configured': bool(self.kb_id),
#                 'requirements': technical_requirements[:500] + "...",
#                 'status': 'success'
#             }
            
#             # Save to S3
#             if output_bucket:
#                 s3_path = self._save_to_s3(result, parsed_key, output_bucket)
#                 result['s3_path'] = s3_path
            
#             print(f"\n[AGENT] ✅ Architecture generated!")
#             print(f"{'='*70}\n")
            
#             return result
            
#         except Exception as e:
#             print(f"[AGENT] ❌ Error: {e}")
#             import traceback
#             traceback.print_exc()
            
#             return {
#                 'status': 'error',
#                 'error': str(e),
#                 'traceback': traceback.format_exc()
#             }
    
#     def _parse_response(self, response) -> Dict:
#         """Parse agent response"""
#         response_text = str(response)
        
#         import re
#         json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
#         if json_match:
#             try:
#                 return {
#                     'status': 'success',
#                     'architecture': json.loads(json_match.group(0)),
#                     'raw_response': response_text[:500]
#                 }
#             except:
#                 pass
        
#         return {
#             'status': 'success',
#             'architecture': {'raw_response': response_text},
#             'note': 'Could not parse JSON'
#         }
    
#     def _save_to_s3(self, result: Dict, parsed_key: str, bucket: str) -> str:
#         """Save to S3"""
#         try:
#             # Extract user prefix from parsed_key
#             user_prefix = parsed_key.split("/")[0]
#             timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
#             out_folder = f"{user_prefix}/aws_architectures/"
#             out_key = f"{out_folder}{os.path.basename(parsed_key).replace('.json','')}_diagram_{timestamp}.json"

#             self.s3.put_object(
#                 Bucket=bucket,
#                 Key=out_key,
#                 Body=json.dumps(result, indent=2).encode("utf-8"),
#                 ContentType="application/json"
#             )
            
#             s3_path = f"s3://{bucket}/{out_key}"
#             print(f"[S3] 💾 Saved: {s3_path}")
#             return s3_path
#         except Exception as e:
#             print(f"[S3] ⚠️  Save failed: {e}")
#             return None


# # ============================================
# # Tool for RFx Integration
# # ============================================

# def create_aws_architecture_tool(kb_id: Optional[str] = None, region: str = "us-east-1"):
#     """
#     Factory to create AWS architecture tool for main.py integration
    
#     Args:
#         kb_id: Knowledge Base ID (optional - can be empty)
#         region: AWS region
    
#     Returns:
#         Strands tool for RFx pipeline
#     """
    
#     @tool
#     def aws_architecture_tool(technical_requirements: str) -> str:
#         """
#         Generate AWS architecture from technical requirements.
#         Searches both Knowledge Base (may be empty) and MCP Server.
        
#         Args:
#             technical_requirements: Technical requirements from parsed RFx
        
#         Returns:
#             JSON with selected template and generated architecture
#         """
#         try:
#             print(f"[AWS-ARCH-TOOL] 🏗️ Starting architecture generation...")
            
#             agent = AWSArchitectureAgent(region=region, kb_id=kb_id)
            
#             result = agent.run(
#                 technical_requirements=technical_requirements,
#                 parsed_key="auto_generated",
#                 output_bucket="presales-rfp-outputs"
#             )
            
#             return json.dumps(result, indent=2)
            
#         except Exception as e:
#             print(f"[AWS-ARCH-TOOL] ❌ Error: {e}")
#             return json.dumps({
#                 'status': 'error',
#                 'error': str(e)
#             })
    
#     return aws_architecture_tool


# # ============================================
# # Standalone Testing
# # ============================================

# if __name__ == "__main__":
#     import sys
    
#     # Configuration
#     KB_ID = "WU6IC1ZQJH"
#     REGION = "us-east-1"
    
#     parsed_key = "ravi/parsed_outputs/RFP_5_20251017_030359_parsed.json"
#     clarification_key = "ravi/clarifications/RFP_5_20251017_030359_parsed_clarifications_20251017_030413.json"
#     bucket_name = "presales-rfp-outputs"
    
#     s3 = boto3.client("s3", region_name=REGION)

#     # --- STEP 1: Load parsed requirements ---
#     print(f"[INFO] Loading parsed requirements from s3://{bucket_name}/{parsed_key}")
#     parsed_obj = s3.get_object(Bucket=bucket_name, Key=parsed_key)
#     parsed_data = json.loads(parsed_obj["Body"].read().decode("utf-8"))
    
#     # --- STEP 2: Load clarifications ---
#     print(f"[INFO] Loading clarifications from s3://{bucket_name}/{clarification_key}")
#     clar_obj = s3.get_object(Bucket=bucket_name, Key=clarification_key)
#     clar_data = json.loads(clar_obj["Body"].read().decode("utf-8"))
    
#     # --- STEP 3: Combine both into a single requirement prompt ---
#     combined_requirements = "### RFP Requirements:\n"
#     combined_requirements += json.dumps(parsed_data, indent=2)
#     combined_requirements += "\n\n### Clarifications:\n"
#     combined_requirements += json.dumps(clar_data, indent=2)
    
#     print(f"[INFO] Combined RFP and Clarifications loaded successfully.")
#     print(f"Testing with KB ID: {KB_ID or 'None (MCP only)'}")
    
#     # Create and run agent - MCP clients must be used in context
#     agent = AWSArchitectureAgent(region=REGION, kb_id=KB_ID)
    
#     # Run inside MCP client context
#     with agent.aws_docs_client, agent.aws_diag_client:
#         result = agent.run(
#             technical_requirements=combined_requirements,
#             parsed_key=parsed_key,
#             output_bucket="presales-rfp-outputs"
#         )
    
#     # Print result
#     print("\n" + "="*70)
#     print("📊 RESULT")
#     print("="*70)
#     print(json.dumps(result, indent=2))





# #!/usr/bin/env python3
# """
# AWS Architecture Agent - Complete Integration
# - Searches Knowledge Base (text annotations with image URIs) - MAY BE EMPTY
# - Searches MCP Server (AWS Reference Architectures) - ALWAYS AVAILABLE
# - Compares results and selects best template
# - Generates custom architecture

# Knowledge Base can be empty initially - populated only after SOW approval.
# Agent handles empty KB gracefully and relies on MCP Server.
# """

# import boto3
# import json
# import os
# from typing import Dict, List, Optional
# from datetime import datetime
# from pathlib import Path
# from mcp import StdioServerParameters
# from mcp.client.stdio import stdio_client
# from strands import Agent, tool
# from strands.models import BedrockModel
# from strands.tools.mcp import MCPClient

# class AWSArchitectureAgent:
#     """
#     AWS Architecture Generation Agent
#     - KB Tool: Searches text annotations (with image URIs) - handles empty KB
#     - MCP Tools: AWS docs and diagrams - primary source
#     - Agent orchestrates and generates custom architecture
#     """
    
#     def __init__(self, region: str = "us-east-1", kb_id: Optional[str] = None):
#         self.region = region
#         self.kb_id = kb_id or "WU6IC1ZQJH"
#         self.s3 = boto3.client("s3", region_name=region)
#         self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        
#         # Initialize MCP Clients - will be started in context manager
#         # Option 1: Using uvx (requires uv to be installed)
#         # Option 2: Using python -m (if packages are pip installed)
        
#         # Check if uvx is available, fallback to python -m
#         import shutil
#         use_uvx = shutil.which("uvx") is not None
        
#         if use_uvx:
#             self.aws_docs_client = MCPClient(
#                 lambda: stdio_client(
#                     StdioServerParameters(
#                         command="uvx", 
#                         args=["awslabs.aws-documentation-mcp-server@latest"]
#                     )
#                 )
#             )
            
#             self.aws_diag_client = MCPClient(
#                 lambda: stdio_client(
#                     StdioServerParameters(
#                         command="uvx", 
#                         args=["awslabs.aws-diagram-mcp-server@latest"]
#                     )
#                 )
#             )
#         else:
#             # Fallback: Try using npx (if MCP servers are npm packages)
#             # or disable MCP tools altogether
#             print("[WARN] uvx not found. MCP tools will be disabled.")
#             print("[WARN] Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh")
#             self.aws_docs_client = None
#             self.aws_diag_client = None
        
#         # Bedrock Model
#         self.bedrock_model = BedrockModel(
#             model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
#             region_name=region,
#             temperature=0.4,
#         )
        
#         self.agent = None
    
#     # ============================================
#     # Knowledge Base Tool (Handles Empty KB)
#     # ============================================
    
#     def _create_kb_tool(self):
#         """Create KB search tool - gracefully handles empty KB"""
#         kb_id = self.kb_id
#         region = self.region
#         s3_client = self.s3
        
#         # Helper functions (outside the tool)
#         def extract_image_uri(content: str) -> Optional[str]:
#             """Extract image S3 URI from annotation content"""
#             import re
#             match = re.search(r'IMAGE_URI:\s*(s3://[^\s\n]+)', content)
#             if match:
#                 return match.group(1)
#             match = re.search(r'REFERENCE_IMAGE:\s*(s3://[^\s\n]+)', content)
#             if match:
#                 return match.group(1)
#             return None
        
#         def extract_title(content: str) -> Optional[str]:
#             """Extract title from annotation"""
#             import re
#             match = re.search(r'Title:\s*([^\n]+)', content)
#             if match:
#                 return match.group(1).strip()
#             return None
        
#         # Now create the actual tool
#         @tool
#         def search_knowledge_base_diagrams(query: str) -> str:
#             """
#             Search Knowledge Base for approved architecture diagrams.
            
#             NOTE: KB may be EMPTY initially - only populated after SOW approval.
#             This tool handles empty KB gracefully.
            
#             Args:
#                 query: Technical requirements or architecture description
            
#             Returns:
#                 JSON with diagrams found (includes image URIs) or empty result
#             """
#             if not kb_id:
#                 return json.dumps({
#                     "status": "skipped",
#                     "message": "Knowledge Base not configured",
#                     "results": [],
#                     "note": "Using only MCP Server for this query"
#                 })
            
#             try:
#                 bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=region)
                
#                 print(f"[KB-TOOL] 🔍 Searching Knowledge Base...")
                
#                 response = bedrock_agent.retrieve(
#                     knowledgeBaseId=kb_id,
#                     retrievalQuery={'text': query},
#                     retrievalConfiguration={
#                         'vectorSearchConfiguration': {
#                             'numberOfResults': 5
#                         }
#                     }
#                 )
                
#                 results = []
#                 for item in response.get('retrievalResults', []):
#                     content = item.get('content', {}).get('text', '')
#                     score = item.get('score', 0)
                    
#                     # Extract image URI from annotation content
#                     image_uri = extract_image_uri(content)
                    
#                     if image_uri:
#                         # Extract title from annotation
#                         title = extract_title(content)
                        
#                         results.append({
#                             'source': 'knowledge_base',
#                             'title': title or 'Company Architecture',
#                             'description': content[:300],
#                             'image_uri': image_uri,
#                             'relevance_score': score,
#                             'has_diagram': True,
#                             'type': 'approved_architecture'
#                         })
                
#                 if results:
#                     print(f"[KB-TOOL] ✅ Found {len(results)} approved diagrams")
#                 else:
#                     print(f"[KB-TOOL] ℹ️  No diagrams in KB yet (empty or no matches)")
                
#                 return json.dumps({
#                     "status": "success",
#                     "source": "knowledge_base",
#                     "results_count": len(results),
#                     "results": results[:3],
#                     "note": "KB may be empty - populated after SOW approval"
#                 }, indent=2)
                
#             except Exception as e:
#                 print(f"[KB-TOOL] ⚠️  KB search failed: {e}")
#                 return json.dumps({
#                     "status": "error",
#                     "source": "knowledge_base",
#                     "error": str(e),
#                     "results": [],
#                     "note": "Falling back to MCP Server only"
#                 })
        
#         return search_knowledge_base_diagrams
    
#     # ============================================
#     # Create Agent with All Tools
#     # ============================================
    
#     def create_agent(self):
#         """Create agent with KB + MCP tools"""
        
#         system_prompt = """You are an expert AWS Solutions Architect specializing in reference architecture selection and design.

# **Your Tools:**

# 1. **search_knowledge_base_diagrams(query)** - Search company's approved architectures
#    - Returns: Previously approved architecture diagrams with image URIs
#    - IMPORTANT: KB may be EMPTY initially - only populated after SOW approval
#    - If empty, this is NORMAL - proceed with MCP tools only

# 2. **MCP Server Tools** - AWS Reference Architectures (ALWAYS AVAILABLE)
#    - Official AWS reference architectures
#    - AWS service documentation
#    - Always use these as primary source if KB is empty

# **Workflow:**

# STEP 1: DUAL SEARCH (KB may be empty - that's OK!)
# - Call search_knowledge_base_diagrams(requirements)
#   * If results found: Great! Use approved company patterns
#   * If empty/error: NORMAL - KB populated only after approval
# - Call MCP tools to search AWS reference architectures
#   * This is PRIMARY source when KB is empty
# - Collect at least 1 diagram from available sources

# STEP 2: SELECT BEST TEMPLATE
# - If KB has results: Consider company-approved patterns first
# - If KB empty: Use MCP reference architectures (this is expected)
# - Score each available template (0-10) for similarity

# STEP 3: GENERATE CUSTOM ARCHITECTURE
# - Use selected template as foundation
# - Adapt to specific requirements
# - Follow AWS Well-Architected Framework
# - Return detailed architecture specification

# **CRITICAL:**
# - Empty KB is NORMAL - don't report as error
# - Always have MCP as fallback
# - Prefer company KB patterns when available
# - Use MCP patterns when KB is empty or no matches

# Return analysis as JSON:
# {
#     "search_results": {
#         "kb_diagrams": [...],  // May be empty
#         "mcp_diagrams": [...]   // Primary source
#     },
#     "selected_template": {
#         "source": "knowledge_base or mcp_server",
#         "title": "...",
#         "reasoning": "..."
#     },
#     "custom_architecture": {
#         "name": "...",
#         "aws_services": [...],
#         "architecture": {...}
#     }
# }
# """
        
#         # Collect KB tool
#         kb_tool = self._create_kb_tool()
        
#         # Get MCP tools - just pass the client objects directly to Agent
#         # The Agent will automatically extract tools from MCP clients
#         try:
#             if self.aws_docs_client and self.aws_diag_client:
#                 print(f"[AGENT] 🔧 Adding MCP clients to agent...")
#                 # Pass MCP clients directly - Agent handles tool extraction
#                 all_tools = [kb_tool, self.aws_docs_client, self.aws_diag_client]
#                 print(f"[AGENT] ✅ Added 1 KB tool + 2 MCP clients")
#             else:
#                 print(f"[AGENT] ⚠️  MCP clients not available (uvx not installed)")
#                 print(f"[AGENT] ℹ️  Using KB tool only")
#                 all_tools = [kb_tool]
#         except Exception as e:
#             print(f"[AGENT] ⚠️  MCP setup failed: {e}")
#             print(f"[AGENT] ℹ️  Using KB tool only")
#             all_tools = [kb_tool]
        
#         self.agent = Agent(
#             model=self.bedrock_model,
#             system_prompt=system_prompt,
#             tools=all_tools
#         )
        
#         return self.agent
    
#     # ============================================
#     # Main Execution
#     # ============================================
    
#     def run(
#         self, 
#         technical_requirements: str,
#         parsed_key: str,
#         output_bucket: Optional[str] = None
#     ) -> Dict:
#         """
#         Generate AWS architecture from requirements
        
#         Args:
#             technical_requirements: Technical requirements from RFx
#             parsed_key: S3 key for the parsed file
#             output_bucket: S3 bucket to save results
        
#         Returns:
#             Architecture with selected template and generation details
#         """
#         print(f"\n{'='*70}")
#         print(f"🏗️ AWS ARCHITECTURE GENERATION")
#         print(f"{'='*70}")
#         print(f"📋 Requirements: {technical_requirements[:100]}...")
#         print(f"🗄️  KB ID: {self.kb_id or 'Not configured (will use MCP only)'}")
        
#         try:
#             # Create agent (must be inside MCP context)
#             if not self.agent:
#                 self.create_agent()
            
#             # Build prompt
#             prompt = f"""Generate AWS reference architecture for these requirements:

# {technical_requirements}

# Workflow:
# 1. Search KB for approved architectures (may be empty - that's OK)
# 2. Search AWS Reference Architectures via MCP
# 3. Compare available diagrams, select BEST template
# 4. Generate custom architecture based on selected template

# Provide complete analysis in JSON format."""

#             print(f"\n[AGENT] 🚀 Generating architecture...")
            
#             # Run agent
#             response = self.agent(prompt)
            
#             # Parse response
#             result = self._parse_response(response)
            
#             # Add metadata
#             result['metadata'] = {
#                 'timestamp': datetime.utcnow().isoformat(),
#                 'kb_configured': bool(self.kb_id),
#                 'requirements': technical_requirements[:500] + "...",
#                 'status': 'success'
#             }
            
#             # Save to S3
#             if output_bucket:
#                 s3_path = self._save_to_s3(result, parsed_key, output_bucket)
#                 result['s3_path'] = s3_path
            
#             print(f"\n[AGENT] ✅ Architecture generated!")
#             print(f"{'='*70}\n")
            
#             return result
            
#         except Exception as e:
#             print(f"[AGENT] ❌ Error: {e}")
#             import traceback
#             traceback.print_exc()
            
#             return {
#                 'status': 'error',
#                 'error': str(e),
#                 'traceback': traceback.format_exc()
#             }
    
#     def _parse_response(self, response) -> Dict:
#         """Parse agent response"""
#         response_text = str(response)
        
#         import re
#         json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
#         if json_match:
#             try:
#                 return {
#                     'status': 'success',
#                     'architecture': json.loads(json_match.group(0)),
#                     'raw_response': response_text[:500]
#                 }
#             except:
#                 pass
        
#         return {
#             'status': 'success',
#             'architecture': {'raw_response': response_text},
#             'note': 'Could not parse JSON'
#         }
    
#     def _save_to_s3(self, result: Dict, parsed_key: str, bucket: str) -> str:
#         """Save to S3"""
#         try:
#             # Extract user prefix from parsed_key
#             user_prefix = parsed_key.split("/")[0]
#             timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
#             out_folder = f"{user_prefix}/aws_architectures/"
#             out_key = f"{out_folder}{os.path.basename(parsed_key).replace('.json','')}_diagram_{timestamp}.json"

#             self.s3.put_object(
#                 Bucket=bucket,
#                 Key=out_key,
#                 Body=json.dumps(result, indent=2).encode("utf-8"),
#                 ContentType="application/json"
#             )
            
#             s3_path = f"s3://{bucket}/{out_key}"
#             print(f"[S3] 💾 Saved: {s3_path}")
#             return s3_path
#         except Exception as e:
#             print(f"[S3] ⚠️  Save failed: {e}")
#             return None


# # ============================================
# # Tool for RFx Integration
# # ============================================

# def create_aws_architecture_tool(kb_id: Optional[str] = None, region: str = "us-east-1"):
#     """
#     Factory to create AWS architecture tool for main.py integration
    
#     Args:
#         kb_id: Knowledge Base ID (optional - can be empty)
#         region: AWS region
    
#     Returns:
#         Strands tool for RFx pipeline
#     """
    
#     @tool
#     def aws_architecture_tool(technical_requirements: str) -> str:
#         """
#         Generate AWS architecture from technical requirements.
#         Searches both Knowledge Base (may be empty) and MCP Server.
        
#         Args:
#             technical_requirements: Technical requirements from parsed RFx
        
#         Returns:
#             JSON with selected template and generated architecture
#         """
#         try:
#             print(f"[AWS-ARCH-TOOL] 🏗️ Starting architecture generation...")
            
#             agent = AWSArchitectureAgent(region=region, kb_id=kb_id)
            
#             result = agent.run(
#                 technical_requirements=technical_requirements,
#                 parsed_key="auto_generated",
#                 output_bucket="presales-rfp-outputs"
#             )
            
#             return json.dumps(result, indent=2)
            
#         except Exception as e:
#             print(f"[AWS-ARCH-TOOL] ❌ Error: {e}")
#             return json.dumps({
#                 'status': 'error',
#                 'error': str(e)
#             })
    
#     return aws_architecture_tool


# # ============================================
# # Standalone Testing
# # ============================================

# if __name__ == "__main__":
#     import sys
    
#     # Configuration
#     KB_ID = "WU6IC1ZQJH"
#     REGION = "us-east-1"
    
#     parsed_key = "ravi/parsed_outputs/RFP_5_20251017_030359_parsed.json"
#     clarification_key = "ravi/clarifications/RFP_5_20251017_030359_parsed_clarifications_20251017_030413.json"
#     bucket_name = "presales-rfp-outputs"
    
#     s3 = boto3.client("s3", region_name=REGION)

#     # --- STEP 1: Load parsed requirements ---
#     print(f"[INFO] Loading parsed requirements from s3://{bucket_name}/{parsed_key}")
#     parsed_obj = s3.get_object(Bucket=bucket_name, Key=parsed_key)
#     parsed_data = json.loads(parsed_obj["Body"].read().decode("utf-8"))
    
#     # --- STEP 2: Load clarifications ---
#     print(f"[INFO] Loading clarifications from s3://{bucket_name}/{clarification_key}")
#     clar_obj = s3.get_object(Bucket=bucket_name, Key=clarification_key)
#     clar_data = json.loads(clar_obj["Body"].read().decode("utf-8"))
    
#     # --- STEP 3: Combine both into a single requirement prompt ---
#     combined_requirements = "### RFP Requirements:\n"
#     combined_requirements += json.dumps(parsed_data, indent=2)
#     combined_requirements += "\n\n### Clarifications:\n"
#     combined_requirements += json.dumps(clar_data, indent=2)
    
#     print(f"[INFO] Combined RFP and Clarifications loaded successfully.")
#     print(f"Testing with KB ID: {KB_ID or 'None (MCP only)'}")
    
#     # Create and run agent - MCP clients must be used in context
#     agent = AWSArchitectureAgent()
    
#     # Run inside MCP client context (only if MCP clients are available)
#     if agent.aws_docs_client and agent.aws_diag_client:
#         with agent.aws_docs_client, agent.aws_diag_client:
#             result = agent.run(
#                 technical_requirements=combined_requirements,
#                 parsed_key=parsed_key,
#                 output_bucket="presales-rfp-outputs"
#             )
#     else:
#         # Run without MCP context (KB tool only)
#         result = agent.run(
#             technical_requirements=combined_requirements,
#             parsed_key=parsed_key,
#             output_bucket="presales-rfp-outputs"
#         )
    
#     # Print result
#     print("\n" + "="*70)
#     print("📊 RESULT")
#     print("="*70)
#     print(json.dumps(result, indent=2))


# #!/usr/bin/env python3
# """
# AWS Architecture Agent - Complete Integration
# - Searches Knowledge Base (text annotations with image URIs) - MAY BE EMPTY
# - Searches MCP Server (AWS Reference Architectures) - ALWAYS AVAILABLE
# - Compares results and selects best template
# - Generates custom architecture

# Knowledge Base can be empty initially - populated only after SOW approval.
# Agent handles empty KB gracefully and relies on MCP Server.
# """

# import boto3
# import json
# import os
# from typing import Dict, List, Optional
# from datetime import datetime
# from pathlib import Path
# from mcp import StdioServerParameters
# from mcp.client.stdio import stdio_client
# from strands import Agent, tool
# from strands.models import BedrockModel
# from strands.tools.mcp import MCPClient

# class AWSArchitectureAgent:
#     """
#     AWS Architecture Generation Agent
#     - KB Tool: Searches text annotations (with image URIs) - handles empty KB
#     - MCP Tools: AWS docs and diagrams - primary source
#     - Agent orchestrates and generates custom architecture
#     """
    
#     def __init__(self, region: str = "us-east-1", kb_id: Optional[str] = None):
#         self.region = region
#         self.kb_id = kb_id or "WU6IC1ZQJH"
#         self.s3 = boto3.client("s3", region_name=region)
#         self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        
#         # Initialize MCP Clients - will be started in context manager
#         # Option 1: Using uvx (requires uv to be installed)
#         # Option 2: Using python -m (if packages are pip installed)
        
#         # Check if uvx is available, fallback to python -m
#         import shutil
#         use_uvx = shutil.which("uvx") is not None
        
#         if use_uvx:
#             self.aws_docs_client = MCPClient(
#                 lambda: stdio_client(
#                     StdioServerParameters(
#                         command="uvx", 
#                         args=["awslabs.aws-documentation-mcp-server@latest"]
#                     )
#                 )
#             )
#             # Safe initialization for diagram server
#             try:
#                 self.aws_diag_client = MCPClient(
#                     lambda: stdio_client(
#                         StdioServerParameters(
#                             command="uvx", 
#                             args=["awslabs.aws-diagram-mcp-server@latest"]
#                         )
#                     )
#                 )
#             except Exception as e:
#                 print(f"[WARN] Diagram MCP server unavailable: {e}")
#                 self.aws_diag_client = None
#                 print("[INFO] Diagram generation disabled, documentation-only mode.")
#             # self.aws_diag_client = MCPClient(
#             #     lambda: stdio_client(
#             #         StdioServerParameters(
#             #             command="uvx", 
#             #             args=["awslabs.aws-diagram-mcp-server@latest"]
#             #         )
#             #     )
#             # )
#         else:
#             # Fallback: Try using npx (if MCP servers are npm packages)
#             # or disable MCP tools altogether
#             print("[WARN] uvx not found. MCP tools will be disabled.")
#             print("[WARN] Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh")
#             self.aws_docs_client = None
#             self.aws_diag_client = None
        
#         # Bedrock Model
#         self.bedrock_model = BedrockModel(
#             model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
#             region_name=region,
#             temperature=0.4,
#         )
        
#         self.agent = None
    
#     # ============================================
#     # Knowledge Base Tool (Handles Empty KB)
#     # ============================================
    
#     def _create_kb_tool(self):
#         """Create KB search tool - gracefully handles empty KB"""
#         kb_id = self.kb_id
#         region = self.region
#         s3_client = self.s3
        
#         # Helper functions (outside the tool)
#         def extract_image_uri(content: str) -> Optional[str]:
#             """Extract image S3 URI from annotation content"""
#             import re
#             match = re.search(r'IMAGE_URI:\s*(s3://[^\s\n]+)', content)
#             if match:
#                 return match.group(1)
#             match = re.search(r'REFERENCE_IMAGE:\s*(s3://[^\s\n]+)', content)
#             if match:
#                 return match.group(1)
#             return None
        
#         def extract_title(content: str) -> Optional[str]:
#             """Extract title from annotation"""
#             import re
#             match = re.search(r'Title:\s*([^\n]+)', content)
#             if match:
#                 return match.group(1).strip()
#             return None
        
#         # Now create the actual tool
#         @tool
#         def search_knowledge_base_diagrams(query: str) -> str:
#             """
#             Search Knowledge Base for approved architecture diagrams.
            
#             NOTE: KB may be EMPTY initially - only populated after SOW approval.
#             This tool handles empty KB gracefully.
            
#             Args:
#                 query: Technical requirements or architecture description
            
#             Returns:
#                 JSON with diagrams found (includes image URIs) or empty result
#             """
#             if not kb_id:
#                 return json.dumps({
#                     "status": "skipped",
#                     "message": "Knowledge Base not configured",
#                     "results": [],
#                     "note": "Using only MCP Server for this query"
#                 })
            
#             try:
#                 bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=region)
                
#                 print(f"[KB-TOOL] 🔍 Searching Knowledge Base...")
                
#                 response = bedrock_agent.retrieve(
#                     knowledgeBaseId=kb_id,
#                     retrievalQuery={'text': query},
#                     retrievalConfiguration={
#                         'vectorSearchConfiguration': {
#                             'numberOfResults': 2
#                         }
#                     }
#                 )
                
#                 results = []
#                 for item in response.get('retrievalResults', []):
#                     content = item.get('content', {}).get('text', '')
#                     score = item.get('score', 0)
                    
#                     # Extract image URI from annotation content
#                     image_uri = extract_image_uri(content)
                    
#                     if image_uri:
#                         # Extract title from annotation
#                         title = extract_title(content)
                        
#                         results.append({
#                             'source': 'knowledge_base',
#                             'title': title or 'Company Architecture',
#                             'description': content[:300],
#                             'image_uri': image_uri,
#                             'relevance_score': score,
#                             'has_diagram': True,
#                             'type': 'approved_architecture'
#                         })
                
#                 if results:
#                     print(f"[KB-TOOL] ✅ Found {len(results)} approved diagrams")
#                 else:
#                     print(f"[KB-TOOL] ℹ️  No diagrams in KB yet (empty or no matches)")
                
#                 return json.dumps({
#                     "status": "success",
#                     "source": "knowledge_base",
#                     "results_count": len(results),
#                     "results": results[:3],
#                     "note": "KB may be empty - populated after SOW approval"
#                 }, indent=2)
                
#             except Exception as e:
#                 print(f"[KB-TOOL] ⚠️  KB search failed: {e}")
#                 return json.dumps({
#                     "status": "error",
#                     "source": "knowledge_base",
#                     "error": str(e),
#                     "results": [],
#                     "note": "Falling back to MCP Server only"
#                 })
        
#         return search_knowledge_base_diagrams
    
#     # ============================================
#     # Create Agent with All Tools
#     # ============================================
    
#     def create_agent(self):
#         """Create agent with KB + MCP tools"""
        
#         system_prompt = """You are an expert AWS Solutions Architect specializing in reference architecture selection and design.

# **Your Tools:**

# 1. **search_knowledge_base_diagrams(query)** - Search company's approved architectures
#    - Returns: Previously approved architecture diagrams with image URIs
#    - IMPORTANT: KB may be EMPTY initially - only populated after SOW approval
#    - If empty, this is NORMAL - proceed with MCP tools only

# 2. **MCP Server Tools** - AWS Reference Architectures (ALWAYS AVAILABLE)
#    - Official AWS reference architectures
#    - AWS service documentation
#    - Always use these as primary source if KB is empty

# **Workflow:**

# STEP 1: DUAL SEARCH (KB may be empty - that's OK!)
# - Call search_knowledge_base_diagrams(requirements)
#   * If results found: Great! Use approved company patterns
#   * If empty/error: NORMAL - KB populated only after approval
# - Call MCP tools to search AWS reference architectures
#   * This is PRIMARY source when KB is empty
# - Collect at least 1 diagram from available sources

# STEP 2: SELECT BEST TEMPLATE
# - If KB has results: Consider company-approved patterns first
# - If KB empty: Use MCP reference architectures (this is expected)
# - Score each available template (0-10) for similarity

# STEP 3: GENERATE CUSTOM ARCHITECTURE
# - Use selected template as foundation
# - Adapt to specific requirements
# - Follow AWS Well-Architected Framework
# - Return detailed architecture specification

# **CRITICAL:**
# - Empty KB is NORMAL - don't report as error
# - Always have MCP as fallback
# - Prefer company KB patterns when available
# - Use MCP patterns when KB is empty or no matches

# Return analysis as JSON:
# {
#     "search_results": {
#         "kb_diagrams": [...],  // May be empty
#         "mcp_diagrams": [...]   // Primary source
#     },
#     "selected_template": {
#         "source": "knowledge_base or mcp_server",
#         "title": "...",
#         "reasoning": "..."
#     },
#     "custom_architecture": {
#         "name": "...",
#         "aws_services": [...],
#         "architecture": {...}
#     }
# }
# """
        
#         # Collect KB tool
#         kb_tool = self._create_kb_tool()
        
#         # Get MCP tools using list_tools_sync()
#         try:
#             if self.aws_docs_client and self.aws_diag_client:
#                 print(f"[AGENT] 🔧 Collecting MCP tools...")
#                 mcp_tools = (
#                     list(self.aws_diag_client.list_tools_sync()) +
#                     list(self.aws_docs_client.list_tools_sync())
#                 )
#                 all_tools = [kb_tool] + mcp_tools
#                 print(f"[AGENT] ✅ Initialized with {len(all_tools)} tools")
#                 print(f"[AGENT]   - KB Tool: 1")
#                 print(f"[AGENT]   - MCP Tools: {len(mcp_tools)}")
#             else:
#                 print(f"[AGENT] ⚠️  MCP clients not available (uvx not installed)")
#                 print(f"[AGENT] ℹ️  Using KB tool only")
#                 all_tools = [kb_tool]
#         except Exception as e:
#             print(f"[AGENT] ⚠️  MCP tools unavailable: {e}")
#             print(f"[AGENT] ℹ️  Using KB tool only")
#             all_tools = [kb_tool]
        
#         self.agent = Agent(
#             model=self.bedrock_model,
#             system_prompt=system_prompt,
#             tools=all_tools
#         )
        
#         return self.agent
    
#     # ============================================
#     # Main Execution
#     # ============================================
    
#     def run(
#         self, 
#         technical_requirements: str,
#         parsed_key: str,
#         output_bucket: Optional[str] = None
#     ) -> Dict:
#         """
#         Generate AWS architecture from requirements
        
#         Args:
#             technical_requirements: Technical requirements from RFx
#             parsed_key: S3 key for the parsed file
#             output_bucket: S3 bucket to save results
        
#         Returns:
#             Architecture with selected template and generation details
#         """
#         print(f"\n{'='*70}")
#         print(f"🏗️ AWS ARCHITECTURE GENERATION")
#         print(f"{'='*70}")
#         print(f"📋 Requirements: {technical_requirements[:100]}...")
#         print(f"🗄️  KB ID: {self.kb_id or 'Not configured (will use MCP only)'}")
        
#         try:
#             # Ensure agent is created
#             if agent.aws_docs_client and agent.aws_diag_client and not self.agent:
#                 # ✅ Start MCP clients first
#                 with agent.aws_docs_client, agent.aws_diag_client:
#                     # ✅ Create agent after MCP servers are running
#                     print(f"[AGENT] ⚠️  Agent not created yet, creating now...")
#                     agent.create_agent()  
            
            
#             # Build prompt
#             prompt = f"""Generate AWS reference architecture for these requirements:

# {technical_requirements}

# Workflow:
# 1. Search KB for approved architectures (may be empty - that's OK)
# 2. Search AWS Reference Architectures via MCP
# 3. Compare available diagrams, select BEST template
# 4. Generate custom architecture based on selected template

# Provide complete analysis in JSON format."""

#             print(f"\n[AGENT] 🚀 Generating architecture...")
            
#             # Run agent (agent must be created inside MCP context)
#             response = self.agent(prompt)
            
#             # Parse response
#             result = self._parse_response(response)
            
#             # Add metadata
#             result['metadata'] = {
#                 'timestamp': datetime.utcnow().isoformat(),
#                 'kb_configured': bool(self.kb_id),
#                 'requirements': technical_requirements[:500] + "...",
#                 'status': 'success'
#             }
            
#             # Save to S3
#             if output_bucket:
#                 s3_path = self._save_to_s3(result, parsed_key, output_bucket)
#                 result['s3_path'] = s3_path
            
#             print(f"\n[AGENT] ✅ Architecture generated!")
#             print(f"{'='*70}\n")
            
#             return result
            
#         except Exception as e:
#             print(f"[AGENT] ❌ Error: {e}")
#             import traceback
#             traceback.print_exc()
            
#             return {
#                 'status': 'error',
#                 'error': str(e),
#                 'traceback': traceback.format_exc()
#             }
    
#     def _parse_response(self, response) -> Dict:
#         """Parse agent response"""
#         response_text = str(response)
        
#         import re
#         json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
#         if json_match:
#             try:
#                 return {
#                     'status': 'success',
#                     'architecture': json.loads(json_match.group(0)),
#                     'raw_response': response_text[:500]
#                 }
#             except:
#                 pass
        
#         return {
#             'status': 'success',
#             'architecture': {'raw_response': response_text},
#             'note': 'Could not parse JSON'
#         }
    
#     def _save_to_s3(self, result: Dict, parsed_key: str, bucket: str) -> str:
#         """Save to S3"""
#         try:
#             # Extract user prefix from parsed_key
#             user_prefix = parsed_key.split("/")[0]
#             timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
#             out_folder = f"{user_prefix}/aws_architectures/"
#             out_key = f"{out_folder}{os.path.basename(parsed_key).replace('.json','')}_diagram_{timestamp}.json"

#             self.s3.put_object(
#                 Bucket=bucket,
#                 Key=out_key,
#                 Body=json.dumps(result, indent=2).encode("utf-8"),
#                 ContentType="application/json"
#             )
            
#             s3_path = f"s3://{bucket}/{out_key}"
#             print(f"[S3] 💾 Saved: {s3_path}")
#             return s3_path
#         except Exception as e:
#             print(f"[S3] ⚠️  Save failed: {e}")
#             return None


# # ============================================
# # Tool for RFx Integration
# # ============================================

# def create_aws_architecture_tool(kb_id: Optional[str] = None, region: str = "us-east-1"):
#     """
#     Factory to create AWS architecture tool for main.py integration
    
#     Args:
#         kb_id: Knowledge Base ID (optional - can be empty)
#         region: AWS region
    
#     Returns:
#         Strands tool for RFx pipeline
#     """
    
#     @tool
#     def aws_architecture_tool(technical_requirements: str) -> str:
#         """
#         Generate AWS architecture from technical requirements.
#         Searches both Knowledge Base (may be empty) and MCP Server.
        
#         Args:
#             technical_requirements: Technical requirements from parsed RFx
        
#         Returns:
#             JSON with selected template and generated architecture
#         """
#         try:
#             print(f"[AWS-ARCH-TOOL] 🏗️ Starting architecture generation...")
            
#             agent = AWSArchitectureAgent(region=region, kb_id=kb_id)
            
#             result = agent.run(
#                 technical_requirements=technical_requirements,
#                 parsed_key="auto_generated",
#                 output_bucket="presales-rfp-outputs"
#             )
            
#             return json.dumps(result, indent=2)
            
#         except Exception as e:
#             print(f"[AWS-ARCH-TOOL] ❌ Error: {e}")
#             return json.dumps({
#                 'status': 'error',
#                 'error': str(e)
#             })
    
#     return aws_architecture_tool


# # ============================================
# # Standalone Testing
# # ============================================

# if __name__ == "__main__":
#     import sys
    
#     # Configuration
#     KB_ID = "WU6IC1ZQJH"
#     REGION = "us-east-1"
    
#     parsed_key = "ravi/parsed_outputs/RFP_5_20251017_030359_parsed.json"
#     clarification_key = "ravi/clarifications/RFP_5_20251017_030359_parsed_clarifications_20251017_030413.json"
#     bucket_name = "presales-rfp-outputs"
    
#     s3 = boto3.client("s3", region_name=REGION)

#     # --- STEP 1: Load parsed requirements ---
#     print(f"[INFO] Loading parsed requirements from s3://{bucket_name}/{parsed_key}")
#     parsed_obj = s3.get_object(Bucket=bucket_name, Key=parsed_key)
#     parsed_data = json.loads(parsed_obj["Body"].read().decode("utf-8"))
    
#     # --- STEP 2: Load clarifications ---
#     print(f"[INFO] Loading clarifications from s3://{bucket_name}/{clarification_key}")
#     clar_obj = s3.get_object(Bucket=bucket_name, Key=clarification_key)
#     clar_data = json.loads(clar_obj["Body"].read().decode("utf-8"))
    
#     # --- STEP 3: Combine both into a single requirement prompt ---
#     combined_requirements = "### RFP Requirements:\n"
#     combined_requirements += json.dumps(parsed_data, indent=2)
#     combined_requirements += "\n\n### Clarifications:\n"
#     combined_requirements += json.dumps(clar_data, indent=2)
    
#     print(f"[INFO] Combined RFP and Clarifications loaded successfully.")
#     print(f"Testing with KB ID: {KB_ID or 'None (MCP only)'}")
    
#     # Create and run agent - MCP clients must be used in context
#     agent = AWSArchitectureAgent(region=REGION, kb_id=KB_ID)
    
#     # CRITICAL: Everything must happen INSIDE the MCP context
#     if agent.aws_docs_client and agent.aws_diag_client:
#         print("[INFO] Starting MCP client sessions...")
#         with agent.aws_docs_client, agent.aws_diag_client:
#             print("[INFO] MCP clients started, creating agent...")
#             agent.create_agent()  # Create agent INSIDE context - this calls list_tools_sync()
            
#             print("[INFO] Running architecture generation...")
#             result = agent.run(
#                 technical_requirements=combined_requirements,
#                 parsed_key=parsed_key,
#                 output_bucket="presales-rfp-outputs"
#             )
#         print("[INFO] MCP client sessions closed")
#     else:
#         # Run without MCP context (KB tool only)
#         print("[INFO] MCP not available, using KB tool only...")
#         agent.create_agent()
#         result = agent.run(
#             technical_requirements=combined_requirements,
#             parsed_key=parsed_key,
#             output_bucket="presales-rfp-outputs"
#         )
    
#     # Print result
#     print("\n" + "="*70)
#     print("📊 RESULT")
#     print("="*70)
#     print(json.dumps(result, indent=2))

#!/usr/bin/env python3
"""
AWS Architecture Agent - Complete Integration
- Searches Knowledge Base (text annotations with image URIs) - MAY BE EMPTY
- Searches MCP Server (AWS Reference Architectures) - ALWAYS AVAILABLE
- Compares results and selects best template
- Generates custom architecture

Knowledge Base can be empty initially - populated only after SOW approval.
Agent handles empty KB gracefully and relies on MCP Server.
"""

import boto3
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient


class AWSArchitectureAgent:
    """
    AWS Architecture Generation Agent
    - KB Tool: Searches text annotations (with image URIs) - handles empty KB
    - MCP Tools: AWS docs and diagrams - primary source
    - Agent orchestrates and generates custom architecture
    """
    
    def __init__(self, region: str = "us-east-1", kb_id: Optional[str] = None):
        self.region = region
        self.kb_id = kb_id or "WU6IC1ZQJH"
        self.s3 = boto3.client("s3", region_name=region)
        self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        
        # Initialize MCP Clients - will be started in context manager
        import shutil
        use_uvx = shutil.which("uvx") is not None
        
        if use_uvx:
            print("[INFO] Setting up MCP clients...")
            
            # Standard docs client (no extra dependencies needed)
            self.aws_docs_client = MCPClient(
                lambda: stdio_client(
                    StdioServerParameters(
                        command="uvx", 
                        args=["awslabs.aws-documentation-mcp-server@latest"]
                    )
                )
            )
            
            # Diagram client with dependency
            # Using --with adds the dependency to the isolated environment
            # uvx caches this, so it's only slow the first time
            self.aws_diag_client = MCPClient(
                lambda: stdio_client(
                    StdioServerParameters(
                        command="uvx",
                        args=[
                            "--with", "jschema-to-python",
                            "--with", "diagrams",      # ← ADD THIS
                            "--with", "graphviz",  
                            "awslabs.aws-diagram-mcp-server@latest"
                        ]
                    )
                )
            )
            print("[INFO] MCP clients configured (first run may be slow, then cached)")
        else:
            print("[WARN] uvx not found. MCP tools will be disabled.")
            print("[WARN] Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh")
            self.aws_docs_client = None
            self.aws_diag_client = None
        
        # Bedrock Model
        self.bedrock_model = BedrockModel(
            model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name=region,
            temperature=0.4,
        )
        
        self.agent = None
    
    # ============================================
    # Knowledge Base Tool (Handles Empty KB)
    # ============================================
    
    def _create_kb_tool(self):
        """Create KB search tool - gracefully handles empty KB"""
        kb_id = self.kb_id
        region = self.region
        s3_client = self.s3
        
        # Helper functions (outside the tool)
        def extract_image_uri(content: str) -> Optional[str]:
            """Extract image S3 URI from annotation content"""
            import re
            match = re.search(r'IMAGE_URI:\s*(s3://[^\s\n]+)', content)
            if match:
                return match.group(1)
            match = re.search(r'REFERENCE_IMAGE:\s*(s3://[^\s\n]+)', content)
            if match:
                return match.group(1)
            return None
        
        def extract_title(content: str) -> Optional[str]:
            """Extract title from annotation"""
            import re
            match = re.search(r'Title:\s*([^\n]+)', content)
            if match:
                return match.group(1).strip()
            return None
        
        # Now create the actual tool
        @tool
        def search_knowledge_base_diagrams(query: str) -> str:
            """
            Search Knowledge Base for approved architecture diagrams.
            
            NOTE: KB may be EMPTY initially - only populated after SOW approval.
            This tool handles empty KB gracefully.
            
            Args:
                query: Technical requirements or architecture description
            
            Returns:
                JSON with diagrams found (includes image URIs) or empty result
            """
            if not kb_id:
                return json.dumps({
                    "status": "skipped",
                    "message": "Knowledge Base not configured",
                    "results": [],
                    "note": "Using only MCP Server for this query"
                })
            
            try:
                bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=region)
                
                print(f"[KB-TOOL] 🔍 Searching Knowledge Base...")
                
                response = bedrock_agent.retrieve(
                    knowledgeBaseId=kb_id,
                    retrievalQuery={'text': query},
                    retrievalConfiguration={
                        'vectorSearchConfiguration': {
                            'numberOfResults': 5
                        }
                    }
                )
                
                results = []
                for item in response.get('retrievalResults', []):
                    content = item.get('content', {}).get('text', '')
                    score = item.get('score', 0)
                    
                    # Extract image URI from annotation content
                    image_uri = extract_image_uri(content)
                    
                    if image_uri:
                        # Extract title from annotation
                        title = extract_title(content)
                        
                        results.append({
                            'source': 'knowledge_base',
                            'title': title or 'Company Architecture',
                            'description': content[:300],
                            'image_uri': image_uri,
                            'relevance_score': score,
                            'has_diagram': True,
                            'type': 'approved_architecture'
                        })
                
                if results:
                    print(f"[KB-TOOL] ✅ Found {len(results)} approved diagrams")
                else:
                    print(f"[KB-TOOL] ℹ️  No diagrams in KB yet (empty or no matches)")
                
                return json.dumps({
                    "status": "success",
                    "source": "knowledge_base",
                    "results_count": len(results),
                    "results": results[:3],
                    "note": "KB may be empty - populated after SOW approval"
                }, indent=2)
                
            except Exception as e:
                print(f"[KB-TOOL] ⚠️  KB search failed: {e}")
                return json.dumps({
                    "status": "error",
                    "source": "knowledge_base",
                    "error": str(e),
                    "results": [],
                    "note": "Falling back to MCP Server only"
                })
        
        return search_knowledge_base_diagrams



    
    # ============================================
    # Create Agent with All Tools
    # ===========================================
    
    def create_agent(self):
        """Create agent with KB + MCP tools"""
        
        system_prompt = """You are an expert AWS Solutions Architect specializing in reference architecture selection and design.

**Your Tools:**

1. **search_knowledge_base_diagrams(query)** - Search company's approved architectures
   - Returns: Previously approved architecture diagrams with image URIs
   - IMPORTANT: KB may be EMPTY initially - only populated after SOW approval
   - If empty, this is NORMAL - proceed with MCP tools

2. **MCP Server Tools** - AWS Reference Architectures
   - get_diagram_examples - View example diagrams that are similar to user prompt and use them as reference template
   - generate_diagram - Create architecture diagrams from reference aws architectural diagram template
   - AWS service documentation tools

**Workflow:**

Step 1:From the requirements, identify:
1. **Application Type Keywords:**
   - "chatbot" → search for: "chatbot architecture", "conversational AI"
   - "e-commerce" → search for: "online store", "shopping cart"

2. **Technical Capabilities:**
   - Authentication → Include "Cognito" in search
   - Real-time updates → Include "WebSocket", "EventBridge"
   - File storage → Include "S3"
   - Database → Include "DynamoDB", "RDS"
   - AI/ML → Include "Bedrock", "SageMaker"
   - API → Include "API Gateway", "AppSync"

3. **Scale Requirements:**
   - "10,000 users" → "scalable", "auto-scaling"
   - "high availability" → "multi-AZ", "fault-tolerant"
   - "global" → "CloudFront", "multi-region"

STEP 2: SEARCH FOR REFERENCE ARCHITECTURES
- Call search_knowledge_base_diagrams(requirements)
- Call get_diagram_examples also for reference patterns

STEP 3: SELECT BEST TEMPLATE
- Score available templates (0-10) for similarity
- Explain which AWS reference pattern matches best

STEP 4: GENERATE CUSTOM ARCHITECTURE WITH DIAGRAM
- Use generate_diagram to create visual diagram from technical requirements and reference architecture diagram as base template
- Store the custom architecture diagram and base template reference architecture diagram in s3 bucket
- Create detailed architecture specification as JSON
- Include diagram file path in response
- Also include reference architectural diagram path in JSON

Return analysis as JSON:
{
    "search_results": {
        "kb_diagrams": [...],
        "reference_patterns": [...]
    },
    "selected_template": {
        "source": "...",
        "title": "...",
        "reasoning": "...",
        "reference_path":"path/to/reference/diagram_title.png"
    },
    "custom_architecture": {
        "name": "...",
        "aws_services": [...],
        "architecture": {...},
        "diagram_path": "path/to/generated/diagram.png"
    }
}
"""
        
        # Collect KB tool
        kb_tool = self._create_kb_tool()
        
        # Get MCP tools using list_tools_sync()
        try:
            if self.aws_docs_client and self.aws_diag_client:
                print(f"[AGENT] 🔧 Collecting MCP tools...")
                mcp_tools = (
                    list(self.aws_diag_client.list_tools_sync()) +
                    list(self.aws_docs_client.list_tools_sync())
                )
                all_tools = [kb_tool] + mcp_tools

                print("all tools list")
                for i in all_tools:
                    print(i)
                print(f"[AGENT] ✅ Initialized with {len(all_tools)} tools")
                print(f"[AGENT]   - KB Tool: 1")
                print(f"[AGENT]   - MCP Tools: {len(mcp_tools)}")
            else:
                print(f"[AGENT] ⚠️  MCP clients not available (uvx not installed)")
                print(f"[AGENT] ℹ️  Using KB tool only")
                all_tools = [kb_tool]
        except Exception as e:
            print(f"[AGENT] ⚠️  MCP tools unavailable: {e}")
            print(f"[AGENT] ℹ️  Using KB tool only")
            all_tools = [kb_tool]
        
        self.agent = Agent(
            model=self.bedrock_model,
            system_prompt=system_prompt,
            tools=all_tools
        )
        
        return self.agent
    
    # ============================================
    # Main Execution
    # ============================================
    
    def run(
        self, 
        technical_requirements: str,
        parsed_key: str,
        output_bucket: Optional[str] = None
    ) -> Dict:
        """
        Generate AWS architecture from requirements
        
        Args:
            technical_requirements: Technical requirements from RFx
            parsed_key: S3 key for the parsed file
            output_bucket: S3 bucket to save results
        
        Returns:
            Architecture with selected template and generation details
        """
        print(f"\n{'='*70}")
        print(f"🏗️ AWS ARCHITECTURE GENERATION")
        print(f"{'='*70}")
        print(f"📋 Requirements: {technical_requirements[:100]}...")
        print(f"🗄️  KB ID: {self.kb_id or 'Not configured (will use MCP only)'}")
        
        try:
           
            # Ensure agent is created
            if not self.agent:
                print(f"[AGENT] ⚠️  Agent not created yet, creating now...")
                self.create_agent()
            
            # Build prompt
            prompt = f"""Generate AWS reference architecture for these requirements:

{technical_requirements}

Workflow:
1. Search KB for approved architectures (may be empty - that's OK)
2. Search AWS Reference Architectures via MCP
3. Compare available diagrams, select BEST template with respect to technical requirements
4. Generate custom architecture based on selected template using the aws-diagram tool that combines:
   - Best practices from the reference architecture
   - Specific requirements from the user
   - Proper AWS service configurations


Provide complete analysis in JSON format and store the custom architecture generated."""

            print(f"\n[AGENT] 🚀 Generating architecture...")
            
            # Run agent (agent must be created inside MCP context)
            response = self.agent(prompt)
            
            # Parse response
            result = self._parse_response(response)
            
            # Add metadata
            result['metadata'] = {
                'timestamp': datetime.utcnow().isoformat(),
                'kb_configured': bool(self.kb_id),
                'requirements': technical_requirements[:500] + "...",
                'status': 'success'
            }
            
            # Save to S3
            if output_bucket:
                s3_path = self._save_to_s3(result, parsed_key, output_bucket)
                result['s3_path'] = s3_path
            
            print(f"\n[AGENT] ✅ Architecture generated!")
            print(f"{'='*70}\n")
            
            return result
            
        except Exception as e:
            print(f"[AGENT] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _parse_response(self, response) -> Dict:
        """Parse agent response"""
        response_text = str(response)
        
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
        if json_match:
            try:
                return {
                    'status': 'success',
                    'architecture': json.loads(json_match.group(0)),
                    'raw_response': response_text[:500]
                }
            except:
                pass
        
        return {
            'status': 'success',
            'architecture': {'raw_response': response_text},
            'note': 'Could not parse JSON'
        }
    
    def _save_to_s3(self, result: Dict, parsed_key: str, bucket: str) -> str:
        """Save to S3"""
        try:
            # Extract user prefix from parsed_key
            user_prefix = parsed_key.split("/")[0]
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            out_folder = f"{user_prefix}/aws_architectures/"
            out_key = f"{out_folder}{os.path.basename(parsed_key).replace('.json','')}_diagram_{timestamp}.json"

            self.s3.put_object(
                Bucket=bucket,
                Key=out_key,
                Body=json.dumps(result, indent=2).encode("utf-8"),
                ContentType="application/json"
            )
            
            s3_path = f"s3://{bucket}/{out_key}"
            print(f"[S3] 💾 Saved: {s3_path}")
            return s3_path
        except Exception as e:
            print(f"[S3] ⚠️  Save failed: {e}")
            return None


# ============================================
# Tool for RFx Integration
# ============================================

def create_aws_architecture_tool(kb_id: Optional[str] = None, region: str = "us-east-1"):
    """
    Factory to create AWS architecture tool for main.py integration
    
    Args:
        kb_id: Knowledge Base ID (optional - can be empty)
        region: AWS region
    
    Returns:
        Strands tool for RFx pipeline
    """
    
    @tool
    def aws_architecture_tool(technical_requirements: str) -> str:
        """
        Generate AWS architecture from technical requirements.
        Searches both Knowledge Base (may be empty) and MCP Server.
        
        Args:
            technical_requirements: Technical requirements from parsed RFx
        
        Returns:
            JSON with selected template and generated architecture
        """
        try:
            print(f"[AWS-ARCH-TOOL] 🏗️ Starting architecture generation...")
            
            agent = AWSArchitectureAgent(region=region, kb_id=kb_id)
            
            result = agent.run(
                technical_requirements=technical_requirements,
                parsed_key="auto_generated",
                output_bucket="presales-rfp-outputs"
            )
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            print(f"[AWS-ARCH-TOOL] ❌ Error: {e}")
            return json.dumps({
                'status': 'error',
                'error': str(e)
            })
    
    return aws_architecture_tool


# ============================================
# Standalone Testing
# ============================================

if __name__ == "__main__":
    import sys
    
    # Configuration
    KB_ID = "WU6IC1ZQJH"
    REGION = "us-east-1"
    
    parsed_key = "ravi/parsed_outputs/RFP_5_20251017_030359_parsed.json"
    clarification_key = "ravi/clarifications/RFP_5_20251017_030359_parsed_clarifications_20251017_030413.json"
    bucket_name = "presales-rfp-outputs"
    
    s3 = boto3.client("s3", region_name=REGION)

    # --- STEP 1: Load parsed requirements ---
    print(f"[INFO] Loading parsed requirements from s3://{bucket_name}/{parsed_key}")
    parsed_obj = s3.get_object(Bucket=bucket_name, Key=parsed_key)
    parsed_data = json.loads(parsed_obj["Body"].read().decode("utf-8"))
    
    # --- STEP 2: Load clarifications ---
    print(f"[INFO] Loading clarifications from s3://{bucket_name}/{clarification_key}")
    clar_obj = s3.get_object(Bucket=bucket_name, Key=clarification_key)
    clar_data = json.loads(clar_obj["Body"].read().decode("utf-8"))
    
    # --- STEP 3: Combine both into a single requirement prompt ---
    combined_requirements = "### RFP Requirements:\n"
    combined_requirements += json.dumps(parsed_data, indent=2)
    combined_requirements += "\n\n### Clarifications:\n"
    combined_requirements += json.dumps(clar_data, indent=2)
    
    print(f"[INFO] Combined RFP and Clarifications loaded successfully.")
    print(f"Testing with KB ID: {KB_ID or 'None (MCP only)'}")
    
    # Create and run agent - MCP clients must be used in context
    agent = AWSArchitectureAgent()
    
    # CRITICAL: Everything must happen INSIDE the MCP context
    if agent.aws_docs_client and agent.aws_diag_client:
        print("[INFO] Starting MCP client sessions...")
        with agent.aws_docs_client, agent.aws_diag_client:
            print("[INFO] MCP clients started, creating agent...")
            agent.create_agent()  # Create agent INSIDE context - this calls list_tools_sync()
            
            print("[INFO] Running architecture generation...")
            result = agent.run(
                technical_requirements=combined_requirements,
                parsed_key=parsed_key,
                output_bucket="presales-rfp-outputs"
            )
        print("[INFO] MCP client sessions closed")
    else:
        # Run without MCP context (KB tool only)
        print("[INFO] MCP not available, using KB tool only...")
        agent.create_agent()
        result = agent.run(
            technical_requirements=combined_requirements,
            parsed_key=parsed_key,
            output_bucket="presales-rfp-outputs"
        )
    
    # Print result
    print("\n" + "="*70)
    print("📊 RESULT")
    print("="*70)
    print(json.dumps(result, indent=2))
