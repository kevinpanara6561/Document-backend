import boto3
import os

def send_email(recipients, subject, body):
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "ap-south-1")
    
    if not aws_access_key_id or not aws_secret_access_key:
        raise ValueError("AWS credentials are not set")
    
    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region
    )
    client = session.client("ses")
    
    try:
        response = client.send_email(
            Source=os.getenv("SES_FROM_EMAIL"),
            Destination={
                "ToAddresses": recipients,
            },
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": body, "Charset": "UTF-8"},
                },
            },
            ReplyToAddresses=[
                os.getenv("SES_FROM_EMAIL"),
            ],
        )
    except Exception as e:
        print(e)
        return False
    return True
