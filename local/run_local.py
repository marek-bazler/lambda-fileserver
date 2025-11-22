#!/usr/bin/env python3
"""Local development server for testing Lambda functions"""
import os
import sys
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

# Set environment variables for local testing
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['BUCKET_NAME'] = 'fileserver-files-local'
os.environ['USERS_TABLE'] = 'fileserver-users'
os.environ['FILES_TABLE'] = 'fileserver-files'

# Configure boto3 to use LocalStack
import boto3
boto3.setup_default_session(
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

# Patch boto3 clients to use LocalStack endpoint
original_client = boto3.client
def patched_client(service_name, **kwargs):
    kwargs['endpoint_url'] = 'http://localhost:4566'
    return original_client(service_name, **kwargs)
boto3.client = patched_client

original_resource = boto3.resource
def patched_resource(service_name, **kwargs):
    kwargs['endpoint_url'] = 'http://localhost:4566'
    return original_resource(service_name, **kwargs)
boto3.resource = patched_resource

# Import Lambda handler
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))
from handler import lambda_handler

app = Flask(__name__)
CORS(app)

@app.route('/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def proxy(path):
    """Proxy requests to Lambda handler"""
    
    # Build Lambda event from Flask request
    event = {
        'path': f'/{path}',
        'httpMethod': request.method,
        'headers': dict(request.headers),
        'queryStringParameters': dict(request.args) if request.args else None,
        'body': request.get_data(as_text=True) if request.data else None
    }
    
    # Call Lambda handler
    response = lambda_handler(event, {})
    
    # Convert Lambda response to Flask response
    return (
        response.get('body', ''),
        response.get('statusCode', 200),
        response.get('headers', {})
    )

if __name__ == '__main__':
    print("=" * 60)
    print("Local File Server Running")
    print("=" * 60)
    print("API Server: http://localhost:5000")
    print("Web UI: http://localhost:8080")
    print("")
    print("Test credentials:")
    print("  Username: test")
    print("  Password: test123")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
