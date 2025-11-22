import json
import boto3
import hashlib
import base64
import os
from datetime import datetime
from decimal import Decimal

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
USERS_TABLE = os.environ['USERS_TABLE']
FILES_TABLE = os.environ['FILES_TABLE']

users_table = dynamodb.Table(USERS_TABLE)
files_table = dynamodb.Table(FILES_TABLE)


def lambda_handler(event, context):
    """Main Lambda handler routing requests"""
    path = event.get('path', '')
    method = event.get('httpMethod', '')
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        if path == '/login' and method == 'POST':
            return handle_login(event, headers)
        elif path == '/files' and method == 'GET':
            return handle_list_files(event, headers)
        elif path == '/upload' and method == 'POST':
            return handle_upload(event, headers)
        elif path == '/download' and method == 'GET':
            return handle_download(event, headers)
        else:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Not found'})}
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}


def handle_login(event, headers):
    """Authenticate user"""
    body = json.loads(event.get('body', '{}'))
    username = body.get('username')
    password = body.get('password')
    
    if not username or not password:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Missing credentials'})}
    
    # Hash password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Check user
    response = users_table.get_item(Key={'username': username})
    user = response.get('Item')
    
    if not user or user['password_hash'] != password_hash:
        return {'statusCode': 401, 'headers': headers, 'body': json.dumps({'error': 'Invalid credentials'})}
    
    # Simple token (in production, use JWT)
    token = base64.b64encode(f"{username}:{password_hash}".encode()).decode()
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'token': token, 'username': username})
    }


def verify_token(event):
    """Verify authentication token"""
    auth_header = event.get('headers', {}).get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]
    try:
        decoded = base64.b64decode(token).decode()
        username, password_hash = decoded.split(':', 1)
        
        response = users_table.get_item(Key={'username': username})
        user = response.get('Item')
        
        if user and user['password_hash'] == password_hash:
            return username
    except:
        pass
    
    return None


def handle_list_files(event, headers):
    """List files for authenticated user"""
    username = verify_token(event)
    if not username:
        return {'statusCode': 401, 'headers': headers, 'body': json.dumps({'error': 'Unauthorized'})}
    
    # Query files by user
    response = files_table.query(
        IndexName='UserIndex',
        KeyConditionExpression='username = :username',
        ExpressionAttributeValues={':username': username}
    )
    
    files = []
    for item in response.get('Items', []):
        files.append({
            'file_id': item['file_id'],
            'filename': item['filename'],
            'size': int(item['size']),
            'uploaded_at': item['uploaded_at'],
            'content_type': item.get('content_type', 'application/octet-stream')
        })
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'files': files})
    }


def handle_upload(event, headers):
    """Handle file upload with duplicate detection"""
    username = verify_token(event)
    if not username:
        return {'statusCode': 401, 'headers': headers, 'body': json.dumps({'error': 'Unauthorized'})}
    
    body = json.loads(event.get('body', '{}'))
    files = body.get('files', [])
    
    if not files:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No files provided'})}
    
    results = []
    
    for file_data in files:
        filename = file_data.get('filename')
        content_base64 = file_data.get('content')
        content_type = file_data.get('content_type', 'application/octet-stream')
        
        if not filename or not content_base64:
            results.append({'filename': filename, 'status': 'error', 'message': 'Missing data'})
            continue
        
        # Decode file content
        content = base64.b64decode(content_base64)
        
        # Calculate hash for deduplication
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Check for duplicate
        response = files_table.query(
            IndexName='HashIndex',
            KeyConditionExpression='file_hash = :hash',
            ExpressionAttributeValues={':hash': file_hash}
        )
        
        if response.get('Items'):
            existing = response['Items'][0]
            results.append({
                'filename': filename,
                'status': 'duplicate',
                'message': f'File already exists as {existing["filename"]}',
                'file_id': existing['file_id']
            })
            continue
        
        # Upload to S3
        file_id = f"{username}/{datetime.utcnow().isoformat()}_{filename}"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=file_id,
            Body=content,
            ContentType=content_type
        )
        
        # Store metadata
        files_table.put_item(Item={
            'file_id': file_id,
            'username': username,
            'filename': filename,
            'file_hash': file_hash,
            'size': len(content),
            'content_type': content_type,
            'uploaded_at': datetime.utcnow().isoformat()
        })
        
        results.append({
            'filename': filename,
            'status': 'success',
            'file_id': file_id,
            'size': len(content)
        })
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'results': results})
    }


def handle_download(event, headers):
    """Handle file download"""
    username = verify_token(event)
    if not username:
        return {'statusCode': 401, 'headers': headers, 'body': json.dumps({'error': 'Unauthorized'})}
    
    file_id = event.get('queryStringParameters', {}).get('file_id')
    if not file_id:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Missing file_id'})}
    
    # Verify file ownership
    response = files_table.get_item(Key={'file_id': file_id})
    file_item = response.get('Item')
    
    if not file_item or file_item['username'] != username:
        return {'statusCode': 403, 'headers': headers, 'body': json.dumps({'error': 'Access denied'})}
    
    # Generate presigned URL (cheaper than proxying through Lambda)
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': file_id},
        ExpiresIn=300  # 5 minutes
    )
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'download_url': url, 'filename': file_item['filename']})
    }
