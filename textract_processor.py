import boto3
import os
import json
import logging
import datetime
from botocore.exceptions import BotoCoreError, ClientError

# Configure CloudWatch logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Collect log messages for S3
s3_logs = []

def log_to_s3(message):
    timestamp = datetime.datetime.utcnow().isoformat()
    entry = f"{timestamp} - {message}"
    s3_logs.append(entry)
    logger.info(entry)

def write_logs_to_s3(s3_client, bucket, key):
    try:
        log_content = "\n".join(s3_logs)
        s3_client.put_object(Bucket=bucket, Key=key, Body=log_content.encode("utf-8"))
        logger.info(f"S3 log written to s3://{bucket}/{key}")
    except Exception as e:
        logger.error(f"Failed to write logs to S3: {e}")

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    textract = boto3.client('textract')
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

    log_bucket = os.environ.get("LOG_BUCKET")
    if not log_bucket:
        raise Exception("LOG_BUCKET environment variable not set")

    log_key = f"logs/lambda-log-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.txt"

    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        log_to_s3(f"Received file: s3://{bucket}/{key}")
    except (KeyError, IndexError) as e:
        log_to_s3(f"Invalid event format: {e}")
        write_logs_to_s3(s3, log_bucket, log_key)
        return {"statusCode": 400, "body": "Invalid S3 event structure"}

    try:
        response = textract.analyze_document(
            Document={'S3Object': {'Bucket': bucket, 'Name': key}},
            FeatureTypes=['TABLES', 'FORMS']
        )
        log_to_s3("Textract analysis complete.")
    except (BotoCoreError, ClientError) as e:
        log_to_s3(f"Textract failed: {e}")
        write_logs_to_s3(s3, log_bucket, log_key)
        return {"statusCode": 500, "body": "Textract processing failed"}

    try:
        extracted_text = "\n".join(
            [block['Text'] for block in response.get('Blocks', []) if block['BlockType'] == 'LINE']
        )
        log_to_s3("Text extraction successful.")
    except Exception as e:
        log_to_s3(f"Text extraction error: {e}")
        write_logs_to_s3(s3, log_bucket, log_key)
        return {"statusCode": 500, "body": "Text extraction failed"}

    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {
                "role": "user",
                "content": f"Analyze this tax document and return structured JSON:\n{extracted_text}"
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.5,
        "top_p": 0.9,
        "stop_sequences": []
    })

    try:
        response = bedrock.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        response_body = json.loads(response['body'].read())
        json_result = response_body.get("content", "")

        # Step 1: Convert list to string if needed
        if isinstance(json_result, list):
            json_result = "\n".join(
                [msg.get("text", "") if isinstance(msg, dict) else str(msg) for msg in json_result]
            )
        elif not isinstance(json_result, str):
            json_result = str(json_result)

        # Step 2: Remove Markdown-style code block lines (```json or ```)
        if isinstance(json_result, str) and json_result.strip().startswith("```"):
            json_result = "\n".join(
                line for line in json_result.strip().splitlines()
                if not line.strip().startswith("```")
            )

        log_to_s3("Bedrock inference complete.")
        log_to_s3(f"Inference JSON Output:\n{json_result}")
    except (BotoCoreError, ClientError, KeyError, json.JSONDecodeError) as e:
        log_to_s3(f"Bedrock inference failed: {e}")
        write_logs_to_s3(s3, log_bucket, log_key)
        return {"statusCode": 500, "body": "Bedrock model invocation failed"}

    try:
        result_key = key.replace("uploads/", "results/").replace(".pdf", ".json")
        s3.put_object(Bucket=bucket, Key=result_key, Body=json_result.encode("utf-8"))
        log_to_s3(f"Result uploaded to s3://{bucket}/{result_key}")
    except (BotoCoreError, ClientError) as e:
        log_to_s3(f"Failed to upload result to S3: {e}")
        write_logs_to_s3(s3, log_bucket, log_key)
        return {"statusCode": 500, "body": "Failed to upload result to S3"}

    write_logs_to_s3(s3, log_bucket, log_key)

    return {
        "statusCode": 200,
        "body": "Textract and Bedrock processing complete"
    }
