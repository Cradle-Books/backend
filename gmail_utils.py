import os
import base64
import random
from email.mime.text import MIMEText

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scope for sending emails
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")


# 🔐 Authenticate and return Gmail service
def get_gmail_service():
    creds = None

    # Load existing token
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no valid creds, login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=8050)

        # Save token for reuse
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ✉️ Send email function
def send_email(to_email, subject, message_text):
    service = get_gmail_service()

    message = MIMEText(message_text)
    message["to"] = to_email
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    body = {"raw": raw_message}

    message = service.users().messages().send(
        userId="me",
        body=body
    ).execute()

    return message



# 📩 Send OTP email
def send_otp_email(user_email, otp):
    subject = "Your Verification Code"
    message = f"""
Hello 👋

Your OTP is: {otp}

This code expires in 10 minutes.

If you didn't request this, ignore this email.
"""

    return send_email(user_email, subject, message)