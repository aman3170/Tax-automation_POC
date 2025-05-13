# Tax-automation_POC

This Proof of Concept demonstrates an end-to-end flow:

- File upload using curl (POST)
- AWS Lambda & S3 for storage
- Textract for document analysis
- AWS Bedrock for natural language processing
- JSON transformation to PDF
- Final PDF stored in S3


## 1. File Upload
Use curl to POST file to AWS API Gateway endpoint.
```
curl -X POST https://<AWS API endpoint>/upload \
  -H "Content-Type: application/pdf" \
  -H "filename: sample1.pdf" \
  --data-binary "@sample1.pdf"
```
## 2. AWS S3 + API Gateway + Lambda (File Upload Handler)

API Gateway receives file → invokes Lambda.
Lambda stores the file in S3 bucket (e.g., s3://your-bucket/uploads/).

## 3. Trigger Textract on File Upload
Use S3 Event Notification to trigger a second Lambda when a file is uploaded.
Lambda uses Textract to analyze document text (form, table, or raw text).

## 4. Call Bedrock model (Anthropic Claude 3 Sonnet)
Parse extracted text and send it to Bedrock's Anthropic model.

## 5. Process Response and Convert to JSON
Receive the structured or refined response from Bedrock.
Parse it into a JSON format suitable for PDF generation.

## 6. Generate PDF from JSON 
Create a PDF and store it back in S3:/processed/filename.pdf.
