import logging
import os
import requests
from sqlalchemy.orm import Session
import boto3
import urllib.parse

from app.libs.s3_service import upload_file_to_s3
from app.libs.utils import generate_id
from app.models import AdminUserModel, DocumentModel
from app.routers.admin.crud.invoices import generate_unique_filename
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
WHATSAPP_API_URL = os.getenv('WHATSAPP_API_URL')
WELCOME_TEMPLATE = os.getenv('WELCOME_TEMPLATE')
CLASSIFICATION_TEMPLATE = os.getenv('CLASSIFICATION_TEMPLATE')

async def receive_data(request, db):
    data = await request.json()

    logging.info(f"Received data: {data}")

    if data and 'entry' in data:
        for entry in data['entry']:
            changes = entry.get('changes', [])
            for change in changes:
                process_change(change, db)

    return {"success": "message received"}

# Process change
def process_change(change, db):
    value = change.get('value', {})
    messages = value.get('messages', [])
    for message in messages:
        process_message(message, db)

def process_message(message, db):
    message_type = message.get('type')
    wa_id = message.get('from')
    
    admin_user = get_admin_user_by_phone(wa_id, db)
    if not admin_user:
        logging.error(f"No admin user found for phone number {wa_id}")
        return
    
    admin_user_id = admin_user.id
    
    if message_type == 'document':
        document = message['document']
        media_id = document['id']
        file_name = document['filename']
        mime_type = document['mime_type']
        
        logging.info(f"Received document: {file_name} (Type: {mime_type})")
        
        file_url = download_media(media_id)
        
        if file_url:
            try:                
                s3_url = save_to_s3(db, file_name, file_url, mime_type)
                create_document(db, s3_url, file_name, mime_type, admin_user_id)
            except Exception as e:
                logging.error(f"Error downloading file content: {str(e)}")
        else:
            logging.error("Failed to download media")

    elif message_type == 'text':
        message_body = message['text']['body']
        logging.info(f"Received message from {wa_id}: {message_body}")
        send_welcome_message_with_image(wa_id)


def download_media(media_id: str):
    try:
        url = f"https://graph.facebook.com/v20.0/{media_id}"
        headers = {
            "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            media_url = response.json().get('url')
            if not media_url:
                logging.error("No media URL found in the response.")
                return None

            encoded_url = urllib.parse.quote(media_url, safe='/:?=&')

            media_response = requests.get(encoded_url, headers=headers)
            if media_response.status_code == 200:
                return media_response.content
            else:
                logging.error(f"Failed to download media: {media_response.text}")
                return None
        else:
            logging.error(f"Failed to fetch media URL: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error downloading media: {str(e)}")
        return None

def save_to_s3(db: Session, file_name: str, file_content: bytes, mime_type: str):
    try:
        original_file_name = file_name
        unique_file_name = generate_unique_filename(db, original_file_name)
        s3_key = f"invoices/{unique_file_name}"
        
        s3_url = upload_file_to_s3(file_content, os.getenv("AWS_BUCKET"), s3_key, mime_type)
        
        logging.info(f"File {unique_file_name} saved to S3 in 'invoices' folder successfully")
        return s3_url
    except Exception as e:
        logging.error(f"Failed to save file to S3: {str(e)}")
        return None



def send_welcome_message_with_image(wa_id: str):
    pass

def create_document(db: Session, file_path: str, file_name: str, file_type: str, admin_user_id: str):
    document = DocumentModel(
        id=generate_id(),
        name=file_name,
        file_path=file_path,
        file_type=file_type,
        admin_user_id=admin_user_id
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    logging.info(f"Document {file_name} saved in the database")
    return document

def get_admin_user_by_phone(phone_number: str, db: Session):
    return db.query(AdminUserModel).filter(AdminUserModel.phone == phone_number).first()

def send_whatsapp_request(payload, success_log, error_log):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        logging.info(success_log)
        return True, None
    else:
        logging.error("%s: %s", error_log, response.text)
        return False, None

def send_welcome_template(recipient_id, name):
    payload = {
    "messaging_product": "whatsapp",
    "recipient_type": "individual",
    "to": recipient_id,
    "type": "template",
    "template": {
        "name": WELCOME_TEMPLATE,
        "language": {
            "code": "en"
        },
        "components": [
            {
                "type": "body",
                "parameters": [
                    {
                        "type": "text",
                        "text": name
                    }
                ]
            }
        ]
    }
}
    send_whatsapp_request(payload, "Template sent successfully.", "Failed to send template.")
    
def send_classification_template(recipient_id, result, category, sub_category):
    payload = {
    "messaging_product": "whatsapp",
    "recipient_type": "individual",
    "to": recipient_id,
    "type": "template",
    "template": {
        "name": CLASSIFICATION_TEMPLATE,
        "language": {
            "code": "en"
        },
        "components": [
            {
                "type": "body",
                "parameters": [
                    {
                        "type": "text",
                        "text": result
                    },
                    {
                        "type": "text",
                        "text": category
                    },
                    {
                        "type": "text",
                        "text": sub_category
                    }
                ]
            }
        ]
    }
}
    send_whatsapp_request(payload, "Template sent successfully.", "Failed to send template.")
