import imapclient
import email
from email.header import decode_header
import sqlite3
import time

# Set your email credentials
username = "kevinpanara6561@gmail.com"
password = "knbl ojby eojj uryc"

# Database setup to store email data
def setup_database():
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            subject TEXT,
            sender TEXT,
            body TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Function to save email data to the database
def save_email(email_id, subject, sender, body):
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO emails (id, subject, sender, body)
        VALUES (?, ?, ?, ?)
    ''', (email_id, subject, sender, body))
    conn.commit()
    conn.close()

# Function to decode email body with fallback encodings
def decode_email_body(part):
    try:
        return part.get_payload(decode=True).decode('utf-8')
    except UnicodeDecodeError:
        return part.get_payload(decode=True).decode('ISO-8859-1')

# Function to fetch and process new emails
def process_new_emails(imap, email_ids):
    for email_id in email_ids:
        print(f"Processing email ID: {email_id}")
        try:
            # Ensure the email_id is a string and properly formatted
            email_id = str(email_id)
            
            # Check if this email has already been processed
            conn = sqlite3.connect("emails.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM emails WHERE id=?", (email_id,))
            result = cursor.fetchone()
            conn.close()

            if result is None:
                print(f"Fetching email ID: {email_id}")
                # Fetch the email by ID
                try:
                    raw_message = imap.fetch([email_id], ['BODY[]', 'FLAGS'])
                    print(f"Fetch result for email ID {email_id}: {raw_message}")

                    if email_id not in raw_message:
                        print(f"Email ID {email_id} not found in fetch result.")
                        continue

                    msg = email.message_from_bytes(raw_message[email_id][b'BODY[]'])

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

                    # Save email to the database
                    save_email(email_id, subject, from_, body)
                    print(f"Email ID {email_id} processed and saved.")

                except Exception as fetch_error:
                    print(f"An error occurred while fetching email ID {email_id}: {fetch_error}")

            else:
                print(f"Email ID {email_id} has already been processed.")
        
        except Exception as e:
            print(f"An error occurred while processing email ID {email_id}: {e}")


def idle_for_new_emails():
    setup_database()

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
