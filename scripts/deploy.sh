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
aws s3 sync ../web/ s3://$(terraform output -raw files_bucket | sed 's/-files-/-web-/')/ --acl public-read

echo ""
echo "Deployment complete!"
echo "API Endpoint: $API_ENDPOINT"
echo "Web UI: http://$WEB_BUCKET"
echo ""
echo "Next steps:"
echo "1. Create a user in DynamoDB users table"
echo "2. Access the web UI and login"
