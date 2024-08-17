import os
import random
from datetime import datetime
from uuid import uuid4
import boto3
import phonenumbers
from sqlalchemy import inspect


def now():
    return datetime.now()


def generate_id():
    id = str(uuid4())
    return id


def generate_otp():
    otp = ""
    while len(otp) < 6:
        otp += str(random.randint(0, 9))
    return otp


def date_time_diff_min(start: datetime, end: datetime):
    duration = end - start
    duration_in_seconds = duration.total_seconds()
    minutes = divmod(duration_in_seconds, 60)[0]
    return minutes


def object_as_dict(obj):
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


def check_number(number):
    try:
        number = str(number)
        number = phonenumbers.parse(number, "IN")
        number = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
        return number
    except Exception as e:
        print(e)
        return False


def file_cleanup():
    dir = "./app/uploads"
    files = os.listdir(dir)
    now = datetime.now()
    for file in files:
        if file == "__init__.py":
            continue

        path = os.path.join(dir, file)
        creation_time = os.path.getctime(path)
        dt_object = datetime.fromtimestamp(creation_time)
        diff = now - dt_object
        if diff.days > 1:
            os.remove(path)


def remove_file(path):
    os.remove(path)
    

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET = os.getenv("AWS_BUCKET")

def connect_to_aws_service(service_name):
    
    service = boto3.client(
        service_name=service_name,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    
    return service, AWS_BUCKET
