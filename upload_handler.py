import boto3
import base64
import uuid

s3 = boto3.client('s3')
BUCKET_NAME = "<s3-bucket-name>"

def lambda_handler(event, context):
    try:
        if 'body' not in event or not event['body']:
            return {
                'statusCode': 400,
                'body': 'Missing file content in request body'
            }

        # Decode base64 (required when binary media type is enabled)
        file_bytes = base64.b64decode(event['body'])

        # Get filename from headers or default to UUID
        filename = event.get('headers', {}).get('filename', str(uuid.uuid4()) + ".pdf")

        # Upload to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=f"uploads/{filename}",
            Body=file_bytes,
            ContentType="application/pdf"
        )

        return {
            'statusCode': 200,
            'body': f"Uploaded to S3 as uploads/{filename}"
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': f"Error: {str(e)}"
        }
