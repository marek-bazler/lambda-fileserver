terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 bucket for file storage
resource "aws_s3_bucket" "files" {
  bucket = "${var.project_name}-files-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_public_access_block" "files" {
  bucket = aws_s3_bucket.files.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket for web UI
resource "aws_s3_bucket" "web" {
  bucket = "${var.project_name}-web-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_website_configuration" "web" {
  bucket = aws_s3_bucket.web.id

  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket = aws_s3_bucket.web.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "web" {
  bucket = aws_s3_bucket.web.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.web.arn}/*"
      }
    ]
  })
}

# DynamoDB tables
resource "aws_dynamodb_table" "users" {
  name           = "${var.project_name}-users"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "username"

  attribute {
    name = "username"
    type = "S"
  }
}

resource "aws_dynamodb_table" "files" {
  name           = "${var.project_name}-files"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "file_id"

  attribute {
    name = "file_id"
    type = "S"
  }

  attribute {
    name = "username"
    type = "S"
  }

  attribute {
    name = "file_hash"
    type = "S"
  }

  global_secondary_index {
    name            = "UserIndex"
    hash_key        = "username"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "HashIndex"
    hash_key        = "file_hash"
    projection_type = "ALL"
  }
}

# Lambda function
resource "aws_lambda_function" "api" {
  filename         = "lambda_function.zip"
  function_name    = "${var.project_name}-api"
  role            = aws_iam_role.lambda.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 512

  environment {
    variables = {
      BUCKET_NAME  = aws_s3_bucket.files.id
      USERS_TABLE  = aws_dynamodb_table.users.name
      FILES_TABLE  = aws_dynamodb_table.files.name
    }
  }
}

# IAM role for Lambda
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.files.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.users.arn,
          aws_dynamodb_table.files.arn,
          "${aws_dynamodb_table.files.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# API Gateway
resource "aws_apigatewayv2_api" "api" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api.invoke_arn
}

resource "aws_apigatewayv2_route" "routes" {
  for_each = toset(["/login", "/files", "/upload", "/download"])

  api_id    = aws_apigatewayv2_api.api.id
  route_key = "ANY ${each.value}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

resource "random_id" "suffix" {
  byte_length = 4
}

# Outputs
output "api_endpoint" {
  value = aws_apigatewayv2_api.api.api_endpoint
}

output "web_url" {
  value = aws_s3_bucket_website_configuration.web.website_endpoint
}

output "files_bucket" {
  value = aws_s3_bucket.files.id
}
