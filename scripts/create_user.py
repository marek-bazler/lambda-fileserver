#!/usr/bin/env python3
import boto3
import hashlib
import sys

if len(sys.argv) != 3:
    print("Usage: python create_user.py <username> <password>")
    sys.exit(1)

username = sys.argv[1]
password = sys.argv[2]

# Hash password
password_hash = hashlib.sha256(password.encode()).hexdigest()

# Store in DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('fileserver-users')  # Update with your table name

table.put_item(Item={
    'username': username,
    'password_hash': password_hash
})

print(f"User '{username}' created successfully!")
