import json
import os

from fastapi import HTTPException, status

DB_USER = os.environ.get("SC_DB_USER")
DB_PASSWORD = os.environ.get("SC_DB_PASSWORD")
DB_HOST = os.environ.get("SC_DB_HOST")
DB_NAME = os.environ.get("SC_DB_NAME")
JWT_KEY = os.environ.get("SC_JWT_KEY")
SMS_API_KEY = os.environ.get("SC_SMS_API_KEY")
SMS_SENDER = os.environ.get("SC_SMS_SENDER")
RP_KEY = os.environ.get("SC_RP_KEY")
RP_SECRET = os.environ.get("SC_RP_SECRET")
RP_WH_SECRET = os.environ.get("SC_RP_WH_SECRET")
RE_CAPTCHA_SECRET = os.environ.get("SC_RE_CAPTCHA_SECRET")
SES_FROM_EMAIL = os.environ.get("SC_SES_FROM_EMAIL")
SES_REGION = os.environ.get("SC_SES_REGION")
AWS_PROFILE = os.environ.get("SC_AWS_PROFILE")
API_KEY = os.environ.get("SC_GOOGLE_TRANS_API_KEY")

# if JWT_KEY:
#     try:
#         JWT_KEY = json.loads(JWT_KEY)
#     except ValueError as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT key"
#         )
# else:
#     raise HTTPException(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="JWT key not set"
#     )
