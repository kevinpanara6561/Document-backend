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

async def receive_data(request, db):
    logging.info("called")
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
    wa_id = message.get('from')  # Extract the phone number from 'from'
    
    # Fetch admin_user_id from the admin_users table
    admin_user = get_admin_user_by_phone(wa_id, db)
    if not admin_user:
        logging.error(f"No admin user found for phone number {wa_id}")
        return
    
    admin_user_id = admin_user.id
    
    if message_type == 'document':
        # Process the document
        document = message['document']
        media_id = document['id']
        file_name = document['filename']
        mime_type = document['mime_type']
        
        # Log the received document details
        logging.info(f"Received document: {file_name} (Type: {mime_type})")
        
        # Download and save the document to S3
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
        
        # Upload the file object to S3 with the correct MIME type
        s3_url = upload_file_to_s3(file_content, os.getenv("AWS_BUCKET"), s3_key, mime_type)
        
        logging.info(f"File {unique_file_name} saved to S3 in 'invoices' folder successfully")
        return s3_url
    except Exception as e:
        logging.error(f"Failed to save file to S3: {str(e)}")
        return None



# Sample send message function (dummy)
def send_welcome_message_with_image(wa_id: str):
    # Implement WhatsApp message sending logic here
    pass

def create_document(db: Session, file_path: str, file_name: str, file_type: str, admin_user_id: str):
    logging.info("caleddddddddddddddd")
    document = DocumentModel(
        id=generate_id(),
        name=file_name,
        file_path=file_path,  # S3 URL
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

