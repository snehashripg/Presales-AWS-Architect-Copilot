# 🚀 Quick Setup Guide

## Step 1: Upload to Cloud9

Upload the entire `frontend/` folder to your Cloud9 environment at `~/environment/frontend/`

## Step 2: Install Dependencies

```bash
cd ~/environment/frontend
npm install
```

**Time**: ~2-3 minutes

## Step 3: Start the Application

```bash
npm start
```

Wait for:
```
Compiled successfully!
You can now view rfx-agent-dashboard in the browser.
Local:            http://localhost:3000
```

## Step 4: Preview in Cloud9

1. Click: **Tools** → **Preview** → **Preview Running Application**
2. Click the **Pop Out** icon (↗️) to open in full browser

## Step 5: Test the Application

### Login
1. Enter email: `your.name@hcltech.com`
2. Click "Sign In"

### Upload RFP
1. Click on upload area
2. Select a PDF or DOCX file
3. Click "Process RFP"
4. Watch progress

### View Results
1. See processing summary
2. Download generated files
3. View formatted results

## 📋 Before Starting

Make sure you have:
- ✅ Lambda functions deployed (`rfx-orchestrator-function`)
- ✅ S3 buckets created (`presales-rfp-inputs`, `presales-rfp-outputs`)
- ✅ Cognito Identity Pool configured
- ✅ A sample RFP file to test with

## 🎯 Expected Flow

```
1. User logs in with @hcltech.com email
   ↓
2. User uploads RFP file
   ↓
3. File uploads to S3 (presales-rfp-inputs)
   ↓
4. Lambda orchestrator is triggered automatically
   ↓
5. Processing runs (4 steps):
   - Parsing
   - Clarifications
   - Pricing
   - SOW Drafting
   ↓
6. Results displayed on screen
   ↓
7. User downloads generated files
```

## ⚠️ Important Notes

1. **Email validation**: Only @hcltech.com emails work
2. **File types**: Only PDF and DOCX are accepted
3. **File size**: Recommend < 10MB for faster upload
4. **Processing time**: Expect 2-5 minutes depending on file size

## 🐛 Troubleshooting

### Port 3000 already in use

```bash
# Kill existing process
killall -9 node
npm start
```

### Dependencies won't install

```bash
# Clear cache and retry
rm -rf node_modules package-lock.json
npm install
```

### Can't preview in Cloud9

1. Make sure app is running (`npm start`)
2. Try manual URL: `https://[YOUR-CLOUD9-URL].vfs.cloud9.us-east-1.amazonaws.com/`

### Upload fails

1. Check S3 bucket permissions
2. Verify Cognito Identity Pool role has S3 write access
3. Check browser console for errors

---

## ✅ Success Criteria

You should be able to:
- ✅ Login with @hcltech.com email
- ✅ Upload RFP file
- ✅ See upload progress (0% → 100%)
- ✅ See processing progress
- ✅ View results summary
- ✅ Download generated files
- ✅ Navigate between Dashboard and Chat tabs

---

**Ready to test? Follow the steps above!** 🎯

