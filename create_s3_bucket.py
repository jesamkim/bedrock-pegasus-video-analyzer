#!/usr/bin/env python3
"""
S3 버킷 생성 및 권한 설정 스크립트
"""

import boto3
import json
from botocore.exceptions import ClientError

def create_s3_bucket():
    """S3 버킷 생성 및 설정"""
    
    # AWS 클라이언트 생성
    s3_client = boto3.client('s3', region_name='us-west-2')
    sts_client = boto3.client('sts', region_name='us-west-2')
    
    # 현재 계정 ID 가져오기
    account_id = sts_client.get_caller_identity()['Account']
    bucket_name = 'bedrock-pegasus-video-temp'
    
    try:
        # 버킷 생성
        print(f"🪣 Creating S3 bucket: {bucket_name}")
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        print(f"✅ Bucket created successfully")
        
        # 버킷 정책 설정 (현재 계정만 접근 가능)
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowCurrentAccount",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": f"arn:aws:iam::{account_id}:root"
                    },
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject"
                    ],
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                },
                {
                    "Sid": "AllowBedrockAccess",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        print(f"🔒 Setting bucket policy...")
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        print(f"✅ Bucket policy set successfully")
        
        # 수명 주기 정책 설정 (임시 파일 자동 삭제)
        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'DeleteTempVideos',
                    'Status': 'Enabled',
                    'Filter': {'Prefix': 'temp-videos/'},
                    'Expiration': {'Days': 1}  # 1일 후 자동 삭제
                }
            ]
        }
        
        print(f"🗑️ Setting lifecycle policy...")
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_config
        )
        print(f"✅ Lifecycle policy set successfully")
        
        print(f"\n🎉 S3 bucket setup completed!")
        print(f"   Bucket: {bucket_name}")
        print(f"   Region: us-west-2")
        print(f"   Account: {account_id}")
        print(f"   Auto-delete: 1 day")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou':
            print(f"✅ Bucket {bucket_name} already exists and is owned by you")
            return True
        elif error_code == 'BucketAlreadyExists':
            print(f"❌ Bucket {bucket_name} already exists but is owned by someone else")
            return False
        else:
            print(f"❌ Error creating bucket: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    create_s3_bucket()
