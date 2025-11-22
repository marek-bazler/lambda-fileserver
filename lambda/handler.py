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
        elif path == '/upload-complete' and method == 'POST':
            return handle_upload_complete(event, headers)
        elif path == '/check-duplicate' and method == 'POST':
            return handle_check_duplicate(event, headers)
        elif path == '/download' and method == 'GET':
            return handle_download(event, headers)
        elif path == '/delete' and method == 'POST':
            return handle_delete(event, headers)
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
    headers = event.get('headers', {})
    # API Gateway may lowercase headers
    auth_header = headers.get('Authorization') or headers.get('authorization', '')
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
    """Generate presigned URLs for direct S3 upload (simple or multipart)"""
    username = verify_token(event)
    if not username:
        return {'statusCode': 401, 'headers': headers, 'body': json.dumps({'error': 'Unauthorized'})}
    
    body = json.loads(event.get('body', '{}'))
    files = body.get('files', [])
    
    if not files:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No files provided'})}
    
    # Multipart threshold: 100MB
    MULTIPART_THRESHOLD = 100 * 1024 * 1024
    
    upload_urls = []
    
    for file_info in files:
        filename = file_info.get('filename')
        content_type = file_info.get('content_type', 'application/octet-stream')
        file_size = file_info.get('size', 0)
        
        if not filename:
            continue
        
        # Generate unique file ID
        file_id = f"{username}/{datetime.utcnow().isoformat()}_{filename}"
        
        # Use multipart upload for large files
        if file_size > MULTIPART_THRESHOLD:
            # Initiate multipart upload
            multipart = s3.create_multipart_upload(
                Bucket=BUCKET_NAME,
                Key=file_id,
                ContentType=content_type
            )
            
            upload_id = multipart['UploadId']
            
            # Calculate part size (10MB chunks)
            part_size = 10 * 1024 * 1024
            num_parts = (file_size + part_size - 1) // part_size
            
            # Generate presigned URLs for each part
            part_urls = []
            for part_num in range(1, num_parts + 1):
                part_url = s3.generate_presigned_url(
                    'upload_part',
                    Params={
                        'Bucket': BUCKET_NAME,
                        'Key': file_id,
                        'UploadId': upload_id,
                        'PartNumber': part_num
                    },
                    ExpiresIn=3600
                )
                part_urls.append(part_url)
            
            upload_urls.append({
                'filename': filename,
                'file_id': file_id,
                'upload_type': 'multipart',
                'upload_id': upload_id,
                'part_size': part_size,
                'part_urls': part_urls,
                'content_type': content_type
            })
        else:
            # Simple upload for smaller files
            presigned_url = s3.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': BUCKET_NAME,
                    'Key': file_id,
                    'ContentType': content_type
                },
                ExpiresIn=3600
            )
            
            upload_urls.append({
                'filename': filename,
                'file_id': file_id,
                'upload_type': 'simple',
                'upload_url': presigned_url,
                'content_type': content_type
            })
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'upload_urls': upload_urls})
    }


def handle_check_duplicate(event, headers):
    """Check if file hash already exists"""
    username = verify_token(event)
    if not username:
        return {'statusCode': 401, 'headers': headers, 'body': json.dumps({'error': 'Unauthorized'})}
    
    body = json.loads(event.get('body', '{}'))
    file_hash = body.get('file_hash')
    
    if not file_hash:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Missing file_hash'})}
    
    # Check for duplicate
    response = files_table.query(
        IndexName='HashIndex',
        KeyConditionExpression='file_hash = :hash',
        ExpressionAttributeValues={':hash': file_hash}
    )
    
    if response.get('Items'):
        existing = response['Items'][0]
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'duplicate': True,
                'existing_file': {
                    'file_id': existing['file_id'],
                    'filename': existing['filename']
                }
            })
        }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'duplicate': False})
    }


def handle_upload_complete(event, headers):
    """Store metadata after successful S3 upload"""
    username = verify_token(event)
    if not username:
        return {'statusCode': 401, 'headers': headers, 'body': json.dumps({'error': 'Unauthorized'})}
    
    body = json.loads(event.get('body', '{}'))
    file_id = body.get('file_id')
    filename = body.get('filename')
    file_hash = body.get('file_hash')
    file_size = body.get('size')
    content_type = body.get('content_type', 'application/octet-stream')
    upload_id = body.get('upload_id')
    parts = body.get('parts')
    
    if not all([file_id, filename, file_hash, file_size]):
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Missing required fields'})}
    
    # Complete multipart upload if applicable
    if upload_id and parts:
        try:
            s3.complete_multipart_upload(
                Bucket=BUCKET_NAME,
                Key=file_id,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
        except Exception as e:
            return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': f'Failed to complete multipart upload: {str(e)}'})}
    else:
        # Verify file exists in S3 for simple uploads
        try:
            s3.head_object(Bucket=BUCKET_NAME, Key=file_id)
        except Exception as e:
            return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': f'File not found in S3: {str(e)}'})}
    
    # Store metadata
    files_table.put_item(Item={
        'file_id': file_id,
        'username': username,
        'filename': filename,
        'file_hash': file_hash,
        'size': int(file_size),
        'content_type': content_type,
        'uploaded_at': datetime.utcnow().isoformat()
    })
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'status': 'success', 'file_id': file_id})
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
    
    # Generate presigned URL (valid for 1 hour for large downloads)
    url = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': file_id,
            'ResponseContentDisposition': f'attachment; filename="{file_item["filename"]}"'
        },
        ExpiresIn=3600  # 1 hour for large files
    )
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'download_url': url, 'filename': file_item['filename']})
    }


def handle_delete(event, headers):
    """Handle file deletion"""
    username = verify_token(event)
    if not username:
        return {'statusCode': 401, 'headers': headers, 'body': json.dumps({'error': 'Unauthorized'})}
    
    body = json.loads(event.get('body', '{}'))
    file_id = body.get('file_id')
    
    if not file_id:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Missing file_id'})}
    
    # Verify file ownership
    response = files_table.get_item(Key={'file_id': file_id})
    file_item = response.get('Item')
    
    if not file_item:
        return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'File not found'})}
    
    if file_item['username'] != username:
        return {'statusCode': 403, 'headers': headers, 'body': json.dumps({'error': 'Access denied'})}
    
    try:
        # Delete from S3
        s3.delete_object(Bucket=BUCKET_NAME, Key=file_id)
        
        # Delete metadata from DynamoDB
        files_table.delete_item(Key={'file_id': file_id})
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'status': 'success', 'message': 'File deleted successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to delete file: {str(e)}'})
        }
