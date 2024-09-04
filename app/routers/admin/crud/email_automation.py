import imapclient
import email
from email.header import decode_header
from app.database import SessionLocal
from app.models import EmailDataModel, EmailModel
import threading
import time

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
        raw_message = imap.fetch([email_id], ['RFC822'])
        
        if not raw_message:
            print(f"No data returned for email ID {email_id}")
        else:
            raw_email = raw_message[email_id][b'RFC822']
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
                    content_type = part.get_content_type()
                    if content_type == "text/plain" or content_type == "text/html":
                        body = decode_email_body(part)
                        break  # Stop after finding the first text or HTML part
            else:
                body = decode_email_body(msg)

            # Save email to the MySQL database using SQLAlchemy
            save_email_to_db(email_id, subject, from_, body)
            print(f"Email ID {email_id} processed and saved.")
    except Exception as e:
        print(f"An error occurred while fetching email ID {email_id}: {e}")

# Function to process new emails
def process_new_emails(imap, email_ids):
    for email_id in email_ids:
        # Start a new thread for each email fetch operation
        thread = threading.Thread(target=fetch_email, args=(imap, email_id))
        thread.start()
        thread.join()  # Wait for the thread to complete

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
                        process_new_emails(imap, email_ids)

                # End IDLE mode
                try:
                    imap.idle_done()
                    print("IDLE mode ended.")
                except Exception as e:
                    print(f"An error occurred while ending IDLE mode: {e}")
                    time.sleep(5)  # Sleep before retrying if unable to end IDLE mode
            
            except Exception as e:
                print(f"An error occurred during IDLE check: {e}")
                imap.idle_done()  # Ensure IDLE is ended on error
                time.sleep(5)  # Sleep before retrying in case of an error
            
            print("Re-entering IDLE mode...")
            try:
                imap.idle()
            except Exception as e:
                print(f"An error occurred while re-entering IDLE mode: {e}")
                time.sleep(5)  # Sleep before retrying if unable to re-enter IDLE mode
    
    finally:
        # Close the connection and logout
        imap.logout()

# Run the email checker using IDLE
idle_for_new_emails()
