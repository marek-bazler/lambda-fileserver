#!/bin/bash
set -e

ENDPOINT="http://localhost:4566"
REGION="us-east-1"

echo "Setting up local AWS resources..."

# Create S3 buckets
echo "Creating S3 buckets..."
aws --endpoint-url=$ENDPOINT s3 mb s3://fileserver-files-local
aws --endpoint-url=$ENDPOINT s3 mb s3://fileserver-web-local

# Create DynamoDB tables
echo "Creating DynamoDB tables..."
aws --endpoint-url=$ENDPOINT dynamodb create-table \
    --table-name fileserver-users \
    --attribute-definitions AttributeName=username,AttributeType=S \
    --key-schema AttributeName=username,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION

aws --endpoint-url=$ENDPOINT dynamodb create-table \
    --table-name fileserver-files \
    --attribute-definitions \
        AttributeName=file_id,AttributeType=S \
        AttributeName=username,AttributeType=S \
        AttributeName=file_hash,AttributeType=S \
    --key-schema AttributeName=file_id,KeyType=HASH \
    --global-secondary-indexes \
        "[{\"IndexName\":\"UserIndex\",\"KeySchema\":[{\"AttributeName\":\"username\",\"KeyType\":\"HASH\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}},{\"IndexName\":\"HashIndex\",\"KeySchema\":[{\"AttributeName\":\"file_hash\",\"KeyType\":\"HASH\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}]" \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION

# Create test user (username: test, password: test123)
echo "Creating test user..."
aws --endpoint-url=$ENDPOINT dynamodb put-item \
    --table-name fileserver-users \
    --item '{"username":{"S":"test"},"password_hash":{"S":"ecd71870d1963316a97e3ac3408c9835ad8cf0f3c1bc703527c30265534f75ae"}}' \
    --region $REGION

echo ""
echo "Local setup complete!"
echo "Test credentials: username=test, password=test123"
