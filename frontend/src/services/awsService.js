// import { Lambda } from '@aws-sdk/client-lambda';
// import { S3Client, PutObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3';
// import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
// import { Upload } from '@aws-sdk/lib-storage';
// import { fromCognitoIdentityPool } from '@aws-sdk/credential-provider-cognito-identity';
// import { CognitoIdentityClient } from '@aws-sdk/client-cognito-identity';

// // AWS Configuration
// const REGION = 'us-east-1';
// const IDENTITY_POOL_ID = 'us-east-1:896efff8-cd15-4b26-a376-189b81e902f8';
// const S3_INPUT_BUCKET = 'presales-rfp-inputs';
// const S3_OUTPUT_BUCKET = 'presales-rfp-outputs';

// // Initialize credentials
// const credentials = fromCognitoIdentityPool({
//   client: new CognitoIdentityClient({ region: REGION }),
//   identityPoolId: IDENTITY_POOL_ID
// });

// // Initialize clients
// const lambdaClient = new Lambda({
//   region: REGION,
//   credentials: credentials
// });

// const s3Client = new S3Client({
//   region: REGION,
//   credentials: credentials
// });

// // Simple simulated progress helper for long-running steps
// // Advances progress gradually up to a ceiling, returns a stop() function
// const startSimulatedProgress = (onTick, options = {}) => {
//   const {
//     start = 5,
//     ceiling = 95,
//     intervalMs = 800,
//     minStep = 1,
//     maxStep = 5
//   } = options;

//   let current = start;
//   let stopped = false;

//   // Emit initial value
//   try { onTick(Math.min(current, ceiling)); } catch (_) {}

//   const id = setInterval(() => {
//     if (stopped) return;
//     // Smaller steps as we get closer to the ceiling
//     const distance = Math.max(0, ceiling - current);
//     const stepBase = Math.max(minStep, Math.min(maxStep, Math.ceil(distance / 10)));
//     const delta = Math.max(minStep, Math.min(maxStep, stepBase));
//     current = Math.min(current + delta, ceiling);
//     try { onTick(current); } catch (_) {}
//     if (current >= ceiling) {
//       clearInterval(id);
//     }
//   }, intervalMs);

//   return () => {
//     stopped = true;
//     clearInterval(id);
//   };
// };

// /**
// * Upload file to S3
// */
// export const uploadFileToS3 = async (file, userEmail, onProgress) => {
//   try {
//     // Create user-specific path
//     const username = userEmail.split('@')[0];
//     const fileName = file.name;
//     const s3Key = `${username}/${fileName}`;

//     const upload = new Upload({
//       client: s3Client,
//       params: {
//         Bucket: S3_INPUT_BUCKET,
//         Key: s3Key,
//         Body: file,
//         ContentType: file.type
//       }
//     });

//     // Track progress
//     upload.on('httpUploadProgress', (progress) => {
//       const percentage = Math.round((progress.loaded / progress.total) * 100);
//       if (onProgress) {
//         onProgress(percentage);
//       }
//     });

//     await upload.done();
    
//     return {
//       success: true,
//       key: s3Key,
//       bucket: S3_INPUT_BUCKET
//     };
//   } catch (error) {
//     console.error('S3 upload error:', error);
//     throw new Error(`Failed to upload file: ${error.message}`);
//   }
// };

// /**
// * Invoke Lambda function
// */
// export const invokeLambdaFunction = async (functionName, payload) => {
//   try {
//     const params = {
//       FunctionName: functionName,
//       InvocationType: 'RequestResponse',
//       Payload: JSON.stringify(payload)
//     };

//     const response = await lambdaClient.invoke(params);
//     const result = JSON.parse(new TextDecoder().decode(response.Payload));
    
//     // Check if Lambda returned an error
//     if (result.statusCode && result.statusCode !== 200) {
//       throw new Error(result.body || 'Lambda execution failed');
//     }

//     return result;
//   } catch (error) {
//     console.error('Lambda invocation error:', error);
//     throw error;
//   }
// };

// /**
// * Process RFP file - Upload to S3 and trigger orchestrator
// */
// export const processRFP = async (file, userEmail, onProgress) => {
//   let stopSim;
//   try {
//     // Step 1: Upload file to S3
//     onProgress && onProgress({ step: 'upload', message: 'Uploading file to S3...', progress: 0 });
    
//     const uploadResult = await uploadFileToS3(file, userEmail, (percentage) => {
//       onProgress && onProgress({ step: 'upload', message: 'Uploading file to S3...', progress: percentage });
//     });

//     onProgress && onProgress({ step: 'upload', message: 'File uploaded successfully', progress: 100 });

//     // Step 2: Trigger orchestrator Lambda
//     onProgress && onProgress({ step: 'process', message: 'Starting RFP processing...', progress: 0 });

//     // Begin simulated progress while Lambda runs
//     stopSim = startSimulatedProgress((p) => {
//       onProgress && onProgress({ step: 'process', message: 'Processing RFP...', progress: p });
//     }, { start: 10, ceiling: 95, intervalMs: 900 });

//     const lambdaPayload = {
//       action: 'runOrchestrator',
//       bucketIn: S3_INPUT_BUCKET,
//       inputKey: uploadResult.key,
//       bucketOut: S3_OUTPUT_BUCKET
//     };

//     const result = await invokeLambdaFunction('rfx-orchestrator-function', lambdaPayload);

//     // Stop simulated progress and complete to 100%
//     try { stopSim && stopSim(); } catch (_) {}
//     onProgress && onProgress({ step: 'process', message: 'Processing complete!', progress: 100 });

//     return {
//       success: true,
//       uploadResult,
//       processingResult: result
//     };
//   } catch (error) {
//     // Ensure any simulation is stopped on error and reflect failure state
//     try { stopSim && stopSim(); } catch (_) {}
//     console.error('RFP processing error:', error);
//     throw error;
//   }
// };

// /**
// * Download file from S3
// */
// export const getS3FileUrl = (bucket, key) => {
//   return `https://${bucket}.s3.${REGION}.amazonaws.com/${key}`;
// };

// /**
// * Generate a presigned URL for S3 GetObject
// */
// export const getPresignedS3Url = async (bucket, key, expiresInSeconds = 900) => {
//   const command = new GetObjectCommand({ Bucket: bucket, Key: key });
//   return await getSignedUrl(s3Client, command, { expiresIn: expiresInSeconds });
// };

// /**
// * Fetch JSON file from S3
// */
// export const fetchS3Json = async (bucket, key) => {
//   try {
//     const url = await getPresignedS3Url(bucket, key);
//     const response = await fetch(url);
//     if (!response.ok) {
//       throw new Error('Failed to fetch file');
//     }
//     return await response.json();
//   } catch (error) {
//     console.error('Error fetching S3 JSON:', error);
//     throw error;
//   }
// };

// export { REGION, IDENTITY_POOL_ID, S3_INPUT_BUCKET, S3_OUTPUT_BUCKET };

// import { Lambda } from '@aws-sdk/client-lambda';
// import { S3Client, PutObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3';
// import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
// import { Upload } from '@aws-sdk/lib-storage';
// import { fromCognitoIdentityPool } from '@aws-sdk/credential-provider-cognito-identity';
// import { CognitoIdentityClient } from '@aws-sdk/client-cognito-identity';

// // AWS Configuration
// const REGION = 'us-east-1';
// const IDENTITY_POOL_ID = 'us-east-1:896efff8-cd15-4b26-a376-189b81e902f8';
// const S3_INPUT_BUCKET = 'presales-rfp-inputs';
// const S3_OUTPUT_BUCKET = 'presales-rfp-outputs';

// // Initialize credentials
// const credentials = fromCognitoIdentityPool({
//   client: new CognitoIdentityClient({ region: REGION }),
//   identityPoolId: IDENTITY_POOL_ID
// });

// // Initialize clients
// const lambdaClient = new Lambda({
//   region: REGION,
//   credentials: credentials
// });

// const s3Client = new S3Client({
//   region: REGION,
//   credentials: credentials
// });

// // Simple simulated progress helper for long-running steps
// // Advances progress gradually up to a ceiling, returns a stop() function
// const startSimulatedProgress = (onTick, options = {}) => {
//   const {
//     start = 5,
//     ceiling = 95,
//     intervalMs = 800,
//     minStep = 1,
//     maxStep = 5
//   } = options;

//   let current = start;
//   let stopped = false;

//   // Emit initial value
//   try { onTick(Math.min(current, ceiling)); } catch (_) {}

//   const id = setInterval(() => {
//     if (stopped) return;
//     // Smaller steps as we get closer to the ceiling
//     const distance = Math.max(0, ceiling - current);
//     const stepBase = Math.max(minStep, Math.min(maxStep, Math.ceil(distance / 10)));
//     const delta = Math.max(minStep, Math.min(maxStep, stepBase));
//     current = Math.min(current + delta, ceiling);
//     try { onTick(current); } catch (_) {}
//     if (current >= ceiling) {
//       clearInterval(id);
//     }
//   }, intervalMs);

//   return () => {
//     stopped = true;
//     clearInterval(id);
//   };
// };

// /**
// * Upload file to S3
// */
// export const uploadFileToS3 = async (file, userEmail, onProgress) => {
//   try {
//     // Create user-specific path
//     const username = userEmail.split('@')[0];
//     const fileName = file.name;
//     const s3Key = `${username}/${fileName}`;

//     const upload = new Upload({
//       client: s3Client,
//       params: {
//         Bucket: S3_INPUT_BUCKET,
//         Key: s3Key,
//         Body: file,
//         ContentType: file.type
//       }
//     });

//     // Track progress
//     upload.on('httpUploadProgress', (progress) => {
//       const percentage = Math.round((progress.loaded / progress.total) * 100);
//       if (onProgress) {
//         onProgress(percentage);
//       }
//     });

//     await upload.done();
    
//     return {
//       success: true,
//       key: s3Key,
//       bucket: S3_INPUT_BUCKET
//     };
//   } catch (error) {
//     console.error('S3 upload error:', error);
//     throw new Error(`Failed to upload file: ${error.message}`);
//   }
// };

// /**
// * Invoke Lambda function
// */
// export const invokeLambdaFunction = async (functionName, payload) => {
//   try {
//     const params = {
//       FunctionName: functionName,
//       InvocationType: 'RequestResponse',
//       Payload: JSON.stringify(payload)
//     };

//     const response = await lambdaClient.invoke(params);
//     const result = JSON.parse(new TextDecoder().decode(response.Payload));
    
//     // Check if Lambda returned an error
//     if (result.statusCode && result.statusCode !== 200) {
//       throw new Error(result.body || 'Lambda execution failed');
//     }

//     return result;
//   } catch (error) {
//     console.error('Lambda invocation error:', error);
//     throw error;
//   }
// };

// /**
// * Process RFP file - Upload to S3 and trigger orchestrator
// */
// export const processRFP = async (file, userEmail, onProgress) => {
//   let stopSim;
//   try {
//     // Step 1: Upload file to S3
//     onProgress && onProgress({ step: 'upload', message: 'Uploading file to S3...', progress: 0 });
    
//     const uploadResult = await uploadFileToS3(file, userEmail, (percentage) => {
//       onProgress && onProgress({ step: 'upload', message: 'Uploading file to S3...', progress: percentage });
//     });

//     onProgress && onProgress({ step: 'upload', message: 'File uploaded successfully', progress: 100 });

//     // Step 2: Trigger orchestrator Lambda
//     onProgress && onProgress({ step: 'process', message: 'Starting RFP processing...', progress: 0 });

//     // Begin simulated progress while Lambda runs
//     stopSim = startSimulatedProgress((p) => {
//       onProgress && onProgress({ step: 'process', message: 'Processing RFP...', progress: p });
//     }, { start: 10, ceiling: 95, intervalMs: 900 });

//     const lambdaPayload = {
//       action: 'runOrchestrator',
//       bucketIn: S3_INPUT_BUCKET,
//       inputKey: uploadResult.key,
//       bucketOut: S3_OUTPUT_BUCKET
//     };

//     const result = await invokeLambdaFunction('rfx-orchestrator-function', lambdaPayload);

//     // Stop simulated progress and complete to 100%
//     try { stopSim && stopSim(); } catch (_) {}
//     onProgress && onProgress({ step: 'process', message: 'Processing complete!', progress: 100 });

//     return {
//       success: true,
//       uploadResult,
//       processingResult: result
//     };
//   } catch (error) {
//     // Ensure any simulation is stopped on error and reflect failure state
//     try { stopSim && stopSim(); } catch (_) {}
//     console.error('RFP processing error:', error);
//     throw error;
//   }
// };

// /**
// * Download file from S3
// */
// export const getS3FileUrl = (bucket, key) => {
//   return `https://${bucket}.s3.${REGION}.amazonaws.com/${key}`;
// };

// /**
// * Generate a presigned URL for S3 GetObject
// */
// export const getPresignedS3Url = async (bucket, key, expiresInSeconds = 900) => {
//   const command = new GetObjectCommand({ Bucket: bucket, Key: key });
//   return await getSignedUrl(s3Client, command, { expiresIn: expiresInSeconds });
// };

// /**
// * Fetch JSON file from S3
// */
// export const fetchS3Json = async (bucket, key) => {
//   try {
//     const url = await getPresignedS3Url(bucket, key);
//     const response = await fetch(url);
//     if (!response.ok) {
//       throw new Error('Failed to fetch file');
//     }
//     return await response.json();
//   } catch (error) {
//     console.error('Error fetching S3 JSON:', error);
//     throw error;
//   }
// };

// export { REGION, IDENTITY_POOL_ID, S3_INPUT_BUCKET, S3_OUTPUT_BUCKET };

import { Lambda } from '@aws-sdk/client-lambda';
import { S3Client, PutObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { Upload } from '@aws-sdk/lib-storage';
import { fromCognitoIdentityPool } from '@aws-sdk/credential-provider-cognito-identity';
import { CognitoIdentityClient } from '@aws-sdk/client-cognito-identity';

// -------------------------
// AWS CONFIGURATION
// -------------------------
const REGION = 'us-east-1';
const IDENTITY_POOL_ID = <Your_Cognito_Pool_ID>;
const S3_INPUT_BUCKET = 'presales-rfp-inputs';
const S3_OUTPUT_BUCKET = 'presales-rfp-outputs';
const LAMBDA_FUNCTION_NAME = 'bedrock-agent-pipeline'; // your Lambda function name

// Initialize credentials
const credentials = fromCognitoIdentityPool({
  client: new CognitoIdentityClient({ region: REGION }),
  identityPoolId: IDENTITY_POOL_ID
});

// Initialize clients
const lambdaClient = new Lambda({ region: REGION, credentials });
const s3Client = new S3Client({ region: REGION, credentials });

// -------------------------
// UTILITIES
// -------------------------
const startSimulatedProgress = (onTick, options = {}) => {
  const { start = 5, ceiling = 95, intervalMs = 800, minStep = 1, maxStep = 5 } = options;
  let current = start;
  let stopped = false;
  try { onTick(Math.min(current, ceiling)); } catch (_) {}

  const id = setInterval(() => {
    if (stopped) return;
    const distance = Math.max(0, ceiling - current);
    const stepBase = Math.max(minStep, Math.min(maxStep, Math.ceil(distance / 10)));
    const delta = Math.max(minStep, Math.min(maxStep, stepBase));
    current = Math.min(current + delta, ceiling);
    try { onTick(current); } catch (_) {}
    if (current >= ceiling) clearInterval(id);
  }, intervalMs);

  return () => { stopped = true; clearInterval(id); };
};

// -------------------------
// FILE UPLOAD TO S3
// -------------------------
export const uploadFileToS3 = async (file, userEmail, onProgress) => {
  try {
    const username = userEmail.split('@')[0];
    const s3Key = `${username}/${Date.now()}_${file.name}`;

    const upload = new Upload({
      client: s3Client,
      params: {
        Bucket: S3_INPUT_BUCKET,
        Key: s3Key,
        Body: file,
        ContentType: file.type
      }
    });

    upload.on('httpUploadProgress', (progress) => {
      const percentage = Math.round((progress.loaded / progress.total) * 100);
      if (onProgress) onProgress(percentage);
    });

    await upload.done();
    return { success: true, key: s3Key, bucket: S3_INPUT_BUCKET };
  } catch (err) {
    console.error('Upload failed:', err);
    throw new Error(`Failed to upload: ${err.message}`);
  }
};

// -------------------------
// INVOKE LAMBDA FUNCTION
// -------------------------
export const invokeLambdaFunction = async (payload) => {
  try {
    const params = {
      FunctionName: LAMBDA_FUNCTION_NAME,
      InvocationType: 'RequestResponse',
      Payload: JSON.stringify(payload)
    };

    const response = await lambdaClient.invoke(params);
    const result = JSON.parse(new TextDecoder().decode(response.Payload));

    if (result.statusCode && result.statusCode !== 200) {
      throw new Error(result.body || 'Lambda returned error');
    }
    return result;
  } catch (err) {
    console.error('Lambda invocation failed:', err);
    throw err;
  }
};

// -------------------------
// MAIN PIPELINE FUNCTION
// -------------------------
export const processRFP = async (file, userEmail, onProgress) => {
  let stopSim;
  try {
    // Step 1: Upload file
    onProgress && onProgress({ step: 'upload', message: 'Uploading file...', progress: 0 });
    const uploadResult = await uploadFileToS3(file, userEmail, (p) =>
      onProgress && onProgress({ step: 'upload', message: 'Uploading to S3...', progress: p })
    );
    onProgress && onProgress({ step: 'upload', message: 'Upload complete', progress: 100 });

    // Step 2: Invoke Bedrock pipeline Lambda
    onProgress && onProgress({ step: 'process', message: 'Invoking Bedrock Agent...', progress: 10 });
    stopSim = startSimulatedProgress(
      (p) => onProgress && onProgress({ step: 'process', message: 'Processing...', progress: p }),
      { start: 10, ceiling: 95, intervalMs: 900 }
    );
     const payload = {
      action: 'full_pipeline',
      bucket: S3_INPUT_BUCKET,
      s3_key: uploadResult.key,
      prompt: "Process RPF"
    };
    

    const result = await invokeLambdaFunction(payload);
    stopSim && stopSim();
    onProgress && onProgress({ step: 'process', message: 'Processing complete!', progress: 100 });

    return { success: true, uploadResult, processingResult: result };
  } catch (err) {
    stopSim && stopSim();
    console.error('Pipeline error:', err);
    throw err;
  }
};

// -------------------------
// S3 HELPERS
// -------------------------
export const getS3FileUrl = (bucket, key) => {
  return `https://${bucket}.s3.${REGION}.amazonaws.com/${key}`;
};

export const getPresignedS3Url = async (bucket, key, expiresInSeconds = 900) => {
  const command = new GetObjectCommand({ Bucket: bucket, Key: key });
  return await getSignedUrl(s3Client, command, { expiresIn: expiresInSeconds });
};

export const fetchS3Json = async (bucket, key) => {
  try {
    const url = await getPresignedS3Url(bucket, key);
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch JSON');
    return await res.json();
  } catch (err) {
    console.error('S3 JSON fetch error:', err);
    throw err;
  }
};

// -------------------------
// DYNAMIC FILE DISCOVERY
// -------------------------
export const listUserFiles = async (bucket, userPrefix, fileType = null) => {
  try {
    const { ListObjectsV2Command } = await import('@aws-sdk/client-s3');
    const command = new ListObjectsV2Command({
      Bucket: bucket,
      Prefix: userPrefix,
      MaxKeys: 1000
    });
    
    const response = await s3Client.send(command);
    let files = response.Contents || [];
    
    // Filter by file type if specified
    if (fileType) {
      files = files.filter(file => {
        const key = file.Key.toLowerCase();
        if (fileType === 'clarifications') {
          return key.includes('clarifications') && key.endsWith('.json');
        } else if (fileType === 'architectures') {
          return key.includes('architecture') && key.endsWith('.json');
        } else if (fileType === 'pricing') {
          return key.includes('pricing') && key.endsWith('.json');
        } else if (fileType === 'sow') {
          return key.includes('sow') && key.endsWith('.docx');
        } else if (fileType === 'parsed') {
          return key.includes('parsed') && key.endsWith('.json') && !key.includes('clarifications') && !key.includes('pricing');
        }
        return key.endsWith('.json') || key.endsWith('.docx');
      });
    }
    
    // Sort by LastModified (newest first)
    files.sort((a, b) => new Date(b.LastModified) - new Date(a.LastModified));
    
    return files;
  } catch (err) {
    console.error('Error listing user files:', err);
    throw err;
  }
};

export const findLatestUserFile = async (bucket, userPrefix, fileType) => {
  try {
    const files = await listUserFiles(bucket, userPrefix, fileType);
    return files.length > 0 ? files[0] : null;
  } catch (err) {
    console.error('Error finding latest file:', err);
    throw err;
  }
};

export const findUserClarifications = async (userEmail) => {
  const username = userEmail.split('@')[0];
  const userPrefix = `${username}/clarifications/`;
  console.log(`[FIND] Looking for clarifications with prefix: ${userPrefix}`);
  const result = await findLatestUserFile(S3_OUTPUT_BUCKET, userPrefix, 'clarifications');
  console.log(`[FIND] Found clarifications:`, result ? result.Key : 'None');
  return result;
};

export const findUserArchitectures = async (userEmail) => {
  const username = userEmail.split('@')[0];
  const userPrefix = `${username}/aws_architectures/`;
  console.log(`[FIND] Looking for architectures with prefix: ${userPrefix}`);
  const result = await findLatestUserFile(S3_OUTPUT_BUCKET, userPrefix, 'architectures');
  console.log(`[FIND] Found architectures:`, result ? result.Key : 'None');
  return result;
};

export const findUserPricing = async (userEmail) => {
  const username = userEmail.split('@')[0];
  const userPrefix = `${username}/pricing_outputs/`;
  console.log(`[FIND] Looking for pricing with prefix: ${userPrefix}`);
  const result = await findLatestUserFile(S3_OUTPUT_BUCKET, userPrefix, 'pricing');
  console.log(`[FIND] Found pricing:`, result ? result.Key : 'None');
  return result;
};

export const findUserSOW = async (userEmail) => {
  const username = userEmail.split('@')[0];
  const userPrefix = `${username}/sow_drafts/`;
  console.log(`[FIND] Looking for SOW with prefix: ${userPrefix}`);
  const result = await findLatestUserFile(S3_OUTPUT_BUCKET, userPrefix, 'sow');
  console.log(`[FIND] Found SOW:`, result ? result.Key : 'None');
  return result;
};

export const findUserParsed = async (userEmail) => {
  const username = userEmail.split('@')[0];
  const userPrefix = `${username}/parsed_outputs/`;
  console.log(`[FIND] Looking for parsed with prefix: ${userPrefix}`);
  const result = await findLatestUserFile(S3_OUTPUT_BUCKET, userPrefix, 'parsed');
  console.log(`[FIND] Found parsed:`, result ? result.Key : 'None');
  return result;
};

// -------------------------
// ARCHITECTURE GALLERY
// -------------------------
export const getRandomArchitectureDiagram = () => {
  // Static list of available architecture diagrams
  const architectureDiagrams = [
    'snehashri.pg/diagrams/RFP_1_20251019_174314_parsed_20251019_174501_custom_diagram.png',
    'snehashri.pg/diagrams/RFP_1_20251018_145341_parsed_20251018_145516_custom_diagram.png'
  ];
  
  // Get random diagram (same for all users based on current date)
  const today = new Date();
  const dayOfYear = Math.floor((today - new Date(today.getFullYear(), 0, 0)) / (1000 * 60 * 60 * 24));
  const randomIndex = dayOfYear % architectureDiagrams.length;
  
  const selectedDiagram = architectureDiagrams[randomIndex];
  console.log(`[GALLERY] Selected diagram for today: ${selectedDiagram}`);
  
  return {
    key: selectedDiagram,
    url: `https://${S3_OUTPUT_BUCKET}.s3.${REGION}.amazonaws.com/${selectedDiagram}`,
    presignedUrl: null // Will be generated when needed
  };
};

export const getArchitectureDiagramUrl = async (diagramKey) => {
  try {
    const url = await getPresignedS3Url(S3_OUTPUT_BUCKET, diagramKey);
    return url;
  } catch (err) {
    console.error('Error generating presigned URL for diagram:', err);
    // Fallback to direct S3 URL
    return `https://${S3_OUTPUT_BUCKET}.s3.${REGION}.amazonaws.com/${diagramKey}`;
  }
};

// -------------------------
// EXPORTS
// -------------------------
export {
  REGION,
  IDENTITY_POOL_ID,
  S3_INPUT_BUCKET,
  S3_OUTPUT_BUCKET
};