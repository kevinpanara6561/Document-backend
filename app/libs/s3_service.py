import io
import os
from botocore.exceptions import NoCredentialsError, ClientError

from app.libs.utils import connect_to_aws_service
import boto3

s3_client, bucket_name = connect_to_aws_service(service_name="s3")

# def upload_file_to_s3(file_name, bucket, object_name=None):
    
#     if object_name is None:
#         object_name = os.path.basename(file_name)
    
#     try:
#         s3_client.upload_file(file_name, bucket_name, object_name)

#     except FileNotFoundError:
#         print(f"The file {file_name} was not found.")

#     except NoCredentialsError:
#         print("Credentials not available.")

#     except ClientError as e:
#         print(f"An error occurred: {e}")

#     return True

def upload_file_to_s3(file_obj, bucket_name, object_name, content_type=None):
    s3_client = boto3.client('s3')
    
    try:
        if isinstance(file_obj, bytes):
            # If file_obj is bytes, convert it to a file-like object
            file_obj = io.BytesIO(file_obj)
        
        # Set default content type if not provided
        content_type = content_type or 'application/octet-stream'

        # Upload the file object to S3
        s3_client.upload_fileobj(
            Fileobj=file_obj,  # file_obj is now a file-like object
            Bucket=bucket_name,
            Key=object_name,
            ExtraArgs={'ContentType': content_type}  # Preserve content type
        )
        
        # Construct and return the S3 URL
        s3_url = object_name
        return s3_url

    except Exception as e:
        print(f"Error uploading file: {e}")
        raise


def get_file_from_s3(bucket, object_name):
    return s3_client.get_object(Bucket=bucket, Key=object_name)

def delete_file_from_s3(bucket, object_name):
    s3_client.delete_object(Bucket=bucket, Key=object_name)
    

# print(get_file_from_s3(bucket_name, "invoices/bill.pdf"))