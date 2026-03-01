#!/bin/bash
# ClaimLens LocalStack Initialization Script
# This script runs when LocalStack container starts

echo "Initializing LocalStack for ClaimLens..."

BUCKET_NAME=${S3_BUCKET_NAME:-claimlens-prod-documents-ap-south-1}

# Wait for LocalStack to be ready
sleep 2

# Create the S3 bucket for document storage
awslocal s3 mb s3://${BUCKET_NAME} 2>/dev/null || true

# Enable versioning on the bucket
awslocal s3api put-bucket-versioning \
    --bucket ${BUCKET_NAME} \
    --versioning-configuration Status=Enabled 2>/dev/null || true

# Set CORS configuration for the bucket
awslocal s3api put-bucket-cors \
    --bucket ${BUCKET_NAME} \
    --cors-configuration '{
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
                "AllowedOrigins": ["http://localhost:3000", "http://127.0.0.1:3000"],
                "ExposeHeaders": ["ETag"]
            }
        ]
    }' 2>/dev/null || true

# List buckets to verify
echo "Created S3 buckets:"
awslocal s3 ls

echo "LocalStack initialization complete!"
