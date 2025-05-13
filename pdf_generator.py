import boto3
import json
import os
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Extracted Document Data", border=False, ln=True, align="C")
        self.ln(5)

    def create_table(self, data_dict):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(200, 220, 255)
        self.cell(60, 10, "Field", border=1, fill=True)
        self.cell(130, 10, "Value", border=1, fill=True)
        self.ln()

        self.set_font("Arial", size=11)
        for k, v in data_dict.items():
            self.cell(60, 10, str(k), border=1)
            # Handle long values
            value = str(v)
            if len(value) > 90:
                value_lines = [value[i:i+90] for i in range(0, len(value), 90)]
                self.cell(130, 10, value_lines[0], border=1)
                self.ln()
                for line in value_lines[1:]:
                    self.cell(60, 10, "", border=0)
                    self.cell(130, 10, line, border=1)
                    self.ln()
            else:
                self.cell(130, 10, value, border=1)
                self.ln()


def lambda_handler(event, context):
    s3 = boto3.client('s3')
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Download and parse JSON content
    obj = s3.get_object(Bucket=bucket, Key=key)
    json_content = json.loads(obj['Body'].read().decode('utf-8'))

    # Create PDF and format as a table
    pdf = PDF()
    pdf.add_page()
    pdf.create_table(json_content)

    # Save to /tmp and upload to S3
    output_key = key.replace("results/", "processed/").replace(".json", ".pdf")
    pdf_output = "/tmp/output.pdf"
    pdf.output(pdf_output)

    with open(pdf_output, 'rb') as f:
        s3.put_object(Bucket=bucket, Key=output_key, Body=f)

    return {
        "statusCode": 200,
        "body": f"PDF generated and uploaded to s3://{bucket}/{output_key}"
    }
