# 🎬 Lambda File Server - Shared Movie Archive

Cost-effective serverless file server for collaborative movie sharing.

**Live Demo:** https://fileshare.bazlers.org

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
- ✅ Direct S3 upload/download (no Lambda proxy)
- ✅ Multipart upload for files >100MB (10MB chunks)
- ✅ Large file support (up to 5TB)
- ✅ Upload progress tracking
- ✅ Batch upload with per-file progress
- ✅ Duplicate detection (SHA256 hash, client-side)
- ✅ Simple web interface
- ✅ Optimized for movies and large files

## Local Testing

Test everything locally before deploying to AWS:

```bash
# 1. Install dependencies (creates virtual environment)
make local-setup

# 2. Start LocalStack + API server
make local-start

# 3. Open browser to http://localhost:8080/index-local.html
# Login with: username=test, password=test123

# Stop services
make local-stop

# Clean everything (including venv)
make clean
```

**Requirements:**
- Docker (for LocalStack)
- Python 3.11+
- AWS CLI (`pip install awscli`)

**Docker Permission Issues?**
If you get "permission denied" errors:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**Note**: Uses a virtual environment (.venv) to avoid dependency conflicts with your system Python/conda.

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
