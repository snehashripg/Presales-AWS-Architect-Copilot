# 🤖 RFx Agent Dashboard

AI-Powered RFP Processing System with Authentication and File Upload

## ✨ Features

- ✅ **Email Authentication** - Only @hcltech.com emails allowed
- ✅ **File Upload** - Drag & drop RFP documents (PDF/DOCX)
- ✅ **Auto-Processing** - Automatically triggers Lambda orchestrator on upload
- ✅ **Real-time Progress** - Live progress tracking during processing
- ✅ **Results Display** - Beautiful formatted display of JSON results
- ✅ **File Downloads** - Download all generated files (DOCX, JSON)
- ✅ **Chat Agent** - Placeholder for future chat functionality
- ✅ **Modern UI** - Clean, responsive design

## 🚀 Quick Start

### Prerequisites

- Node.js 16+ installed
- Access to AWS environment (Lambda functions deployed)
- Cognito Identity Pool configured

### Installation

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

### Running in Cloud9

```bash
# Navigate to frontend
cd ~/environment/frontend

# Install dependencies (if not already done)
npm install

# Start the app
npm start

# Preview in Cloud9
# Click: Tools → Preview → Preview Running Application
```

The app will open at `http://localhost:3000`

## 📋 How to Use

### 1. Login

- Open the app
- Enter your **@hcltech.com** email address
- Click "Sign In"

### 2. Upload RFP

- Click on the upload area or select file
- Choose a PDF or DOCX file
- Click "Process RFP"
- Watch real-time progress

### 3. View Results

- See processing summary
- View each step's status
- Download generated files
- View formatted JSON data

### 4. Download Files

- Click "Download" button next to any file
- Files include:
  - Parsed RFP (JSON)
  - Clarifications (JSON)
  - Pricing Estimate (JSON)
  - Statement of Work (DOCX)

## 🔧 Configuration

### AWS Settings

Edit `src/services/awsService.js`:

```javascript
const REGION = 'us-east-1';
const IDENTITY_POOL_ID = 'us-east-1:896efff8-cd15-4b26-a376-189b81e902f8';
const S3_INPUT_BUCKET = 'presales-rfp-inputs';
const S3_OUTPUT_BUCKET = 'presales-rfp-outputs';
```

### Lambda Functions

The app invokes these Lambda functions:
- `rfx-orchestrator-function` - Main pipeline

Make sure these functions are deployed and accessible.

## 📦 Build for Production

```bash
# Create production build
npm run build

# Deploy to S3
aws s3 sync build/ s3://your-bucket-name/
```

## 🎨 Features Breakdown

### Authentication
- Email validation for @hcltech.com domain
- Simple session-based authentication
- Logout functionality

### File Upload
- Drag & drop interface
- File type validation (PDF, DOCX only)
- Upload progress tracking
- Direct S3 upload

### Processing
- Automatic Lambda orchestrator trigger
- Real-time progress updates
- Step-by-step execution tracking
- Error handling

### Results Display
- Processing summary cards
- Step-by-step status
- Download buttons for all outputs
- Formatted JSON viewer
- Raw JSON details (collapsible)

### Navigation
- Dashboard (main page)
- Chat with Agent (coming soon)
- User profile display
- Logout button

## 🔒 Security

- Cognito Identity Pool for authentication
- Direct Lambda invocation (no public URLs)
- File type validation
- Email domain restriction

## 🐛 Troubleshooting

### Issue: "AccessDenied" when uploading

**Solution**: Check Cognito Identity Pool permissions for S3 and Lambda

### Issue: File upload fails

**Solution**: Verify S3 bucket exists and has proper permissions

### Issue: Lambda invocation fails

**Solution**: 
1. Check Lambda function names match
2. Verify Lambda functions are deployed
3. Check CloudWatch logs

### Issue: Results not displaying

**Solution**: Check browser console for errors and verify S3 output bucket

## 📚 Technology Stack

- **React 18** - Frontend framework
- **React Router** - Navigation
- **AWS SDK v3** - AWS services integration
  - Lambda Client
  - S3 Client
  - Cognito Identity
- **CSS3** - Styling (no external UI frameworks)

## 🎯 Next Steps

- [ ] Implement real chat functionality
- [ ] Add user profile management
- [ ] Implement file preview
- [ ] Add batch processing
- [ ] Enhanced error handling
- [ ] Add unit tests

## 📞 Support

For issues or questions:
1. Check CloudWatch logs for Lambda errors
2. Review browser console for frontend errors
3. Verify AWS permissions

---

**Built with ❤️ for AWS Hackathon 2025**

