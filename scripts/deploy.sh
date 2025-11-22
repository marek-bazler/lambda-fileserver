#!/bin/bash
set -e

echo "Building Lambda deployment package..."
cd lambda
pip install -r requirements.txt -t .
zip -r ../terraform/lambda_function.zip . -x "*.pyc" "__pycache__/*"
cd ..

echo "Deploying infrastructure..."
cd terraform
terraform init
terraform apply -auto-approve

echo "Getting outputs..."
API_ENDPOINT=$(terraform output -raw api_endpoint)
WEB_BUCKET=$(terraform output -raw web_url)

echo "Updating web UI with API endpoint..."
sed -i "s|YOUR_API_ENDPOINT_HERE|$API_ENDPOINT|g" ../web/index.html

echo "Uploading web UI..."
WEB_BUCKET=$(terraform output -raw web_bucket)
aws s3 sync ../web/ s3://$WEB_BUCKET/ --exclude "index-local.html" --exclude "*.bak"

echo "Invalidating CloudFront cache..."
DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id)
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"

echo ""
echo "Deployment complete!"
WEB_URL=$(terraform output -raw web_url)
echo "API Endpoint: $API_ENDPOINT"
echo "Web UI: $WEB_URL (HTTPS enabled)"
echo ""
echo "Next steps:"
echo "1. Create a user in DynamoDB users table"
echo "2. Access the web UI and login"
