import imapclient
import email
from email.header import decode_header
from app.database import SessionLocal
from app.libs.utils import generate_id
from app.models import DocumentModel, EmailDataModel, EmailModel
import threading
import time

from app.routers.admin.crud.whatsapp import save_to_s3

# Set up your email credentials
db = SessionLocal()
db_email = db.query(EmailModel).filter(EmailModel.is_deleted == False).first()
username = db_email.email
password = db_email.password

# Function to save email data to the database using SQLAlchemy
def save_email_to_db(email_id, subject, sender, body):
    try:
        new_email = EmailDataModel(
            id=email_id,
            sender=sender,
            subject=subject,
            body=body,
            email_id=db_email.id,  # Foreign key reference to EmailModel
        )
        db.add(new_email)
        db.commit()
        print(f"Email ID {email_id} saved successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error saving email ID {email_id}: {e}")

def save_email_document(file_name,file_path,file_type,admin_user_id):
    try:
        email = DocumentModel(
            id=generate_id(),
            name=file_name,
            file_path=file_path,
            file_type=file_type,
            admin_user_id=admin_user_id
        )
        db.add(email)
        db.commit()
        db.refresh(email)
    except Exception as e:
        db.rollback()
        print(f"Error saving email : {e}")

# Function to decode email body with fallback encodings
def decode_email_body(part):
    try:
        return part.get_payload(decode=True).decode('utf-8')
    except UnicodeDecodeError:
        return part.get_payload(decode=True).decode('ISO-8859-1')

# Function to fetch and process a single email
def fetch_email(imap, email_id):
    try:
        print(f"Fetching email ID: {email_id}")
        messages = imap.search(['UNSEEN'])
        latest_email_id = max(messages)
        raw_message = imap.fetch([str(latest_email_id).encode()], ['RFC822'])
        
        if not raw_message:
            print(f"No data returned for email ID {latest_email_id}")
        else:
            raw_email = raw_message[latest_email_id][b'RFC822']
            msg = email.message_from_bytes(raw_email)

            # Decode the email subject
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else 'utf-8')

            # Decode the email sender
            from_ = msg.get("From")

            # Get the email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    attachment = part.get_content_disposition()
                    content_type = part.get_content_type()
                    if attachment:
                        if attachment == "attachment":
                            file_name = part.get_filename()
                            mime_type = part.get_content_type()
                            file_content = part.get_payload(decode=True)
                            file_path = save_to_s3(db=db, file_name=file_name, file_content=file_content, mime_type=mime_type)
                            save_email_document(file_name=file_name, file_path=file_path, file_type=mime_type, admin_user_id=db_email.admin_user_id)
                            print("yes its attachment")
                    if content_type == "text/plain" or content_type == "text/html":
                        if body:
                            continue
                        else:
                            body = decode_email_body(part)
                        # break  # Stop after finding the first text or HTML part
            else:
                body = decode_email_body(msg)
            # print(body)
            # Save email to the MySQL database using SQLAlchemy
            save_email_to_db(latest_email_id, subject, from_, body)
            print(f"Email ID {latest_email_id} processed and saved.")
    except Exception as e:
        print(f"An error occurred while fetching email ID {email_id}: {e}")

# Function to process new emails
def process_new_emails(imap, email_ids):
    for email_id in email_ids:
        fetch_email(imap,email_id)

def idle_for_new_emails():
    # Connect to the IMAP server
    imap_server = "imap.gmail.com"
    imap = imapclient.IMAPClient(imap_server, ssl=True)

    # Log in to the server
    imap.login(username, password)

    # Select the mailbox (INBOX by default)
    imap.select_folder("INBOX", readonly=False)
    
    print("Waiting for new emails...")

    try:
        while True:
            try:
                print("Entering IDLE mode...")
                # Use IDLE to wait for new emails
                imap.idle()

                # Wait for a response from the server
                response = imap.idle_check()

                if response:
                    print("Response received:")
                    print(response)
                    # Extract email IDs from the response
                    email_ids = [str(uid[0]) for uid in response if isinstance(uid, tuple) and uid[1] == b'EXISTS']
                    if email_ids:
                        print("New email(s) received!")
                        imap.idle_done()
                        process_new_emails(imap, email_ids)
            
            except Exception as e:
                print(f"An error occurred during IDLE check: {e}")
                imap.idle_done()  # Ensure IDLE is ended on error
                time.sleep(5)  # Sleep before retrying in case of an error
            
            print("Re-entering IDLE mode...")
            # try:
            #     imap.idle()
            # except Exception as e:
            #     print(f"An error occurred while re-entering IDLE mode: {e}")
            #     time.sleep(5)  # Sleep before retrying if unable to re-enter IDLE mode
    
    finally:
        # Close the connection and logout
        imap.logout()

# Run the email checker using IDLE
idle_for_new_emails()
