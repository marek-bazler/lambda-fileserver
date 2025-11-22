# AWS Lambda File Server

Cost-effective serverless file server for occasional archive access.

## Architecture
- **Lambda Functions**: Handle API requests (auth, upload, download, list)
- **S3**: File storage + static web hosting
- **DynamoDB**: User credentials + file metadata (for deduplication)
- **API Gateway**: REST API endpoint

## Cost Estimate (Monthly)
- Lambda: ~$0.20 (1M requests free tier)
- S3: $0.023/GB storage + $0.0004/1000 GET requests
- DynamoDB: Free tier (25GB, 25 RCU/WCU)
- API Gateway: $3.50/million requests (1M free first year)

**For occasional use: ~$1-5/month**

## Features
- ✅ User authentication
- ✅ File upload (single + batch)
- ✅ File download
- ✅ List files by user
- ✅ Duplicate detection (SHA256 hash)
- ✅ Simple web interface

## Local Testing

Test everything locally before deploying to AWS:

```bash
# Install local dependencies
make local-setup

# Start LocalStack + API server
make local-start

# Open browser to http://localhost:8080/index-local.html
# Login with: username=test, password=test123

# Stop services
make local-stop
```

## AWS Deployment

```bash
# Install dependencies
pip install -r lambda/requirements.txt

# Deploy infrastructure
./scripts/deploy.sh

# Create a user
python scripts/create_user.py myusername mypassword
```

## Usage
1. Access web UI at S3 static website URL (or localhost for testing)
2. Login with credentials
3. Upload/download files through the interface
