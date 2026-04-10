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
            try:
                creds.refresh(Request())
                # Save refreshed token back to file
                with open(TOKEN_PATH, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                # If refresh fails, re-authenticate
                print(f"Token refresh failed: {e}. Re-authenticating...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=8050)
                # Save new token
                with open(TOKEN_PATH, "w") as token:
                    token.write(creds.to_json())
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
def send_email(to_email, subject, message_text, is_html=False):
    """
    Send email via Gmail
    
    Args:
        to_email: Recipient email
        subject: Email subject line
        message_text: Email body (HTML if is_html=True, plain text otherwise)
        is_html: Whether to send as HTML email (default: False for plain text)
    """
    service = get_gmail_service()

    # Determine MIME type based on is_html flag
    mime_type = 'html' if is_html else 'plain'
    
    message = MIMEText(message_text, mime_type)
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


# 📩 Send password reset email
def send_reset_email(user_email, reset_token, frontend_url="http://localhost:3000"):
    """
    Send password reset email with clickable link
    
    Args:
        user_email: User's email address
        reset_token: Unique token generated for password reset
        frontend_url: Frontend base URL (default: localhost for development)
    """
    subject = "Reset Your Password - Azaniah"
    
    # Build reset link that frontend will use
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"
    
    # HTML email with professional styling
    message = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 8px;">
          
          <!-- Header -->
          <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #007bff; margin: 0;">Azaniah</h1>
            <p style="color: #666; margin: 5px 0 0 0;">Password Reset Request</p>
          </div>
          
          <!-- Main Content -->
          <div style="background-color: white; padding: 30px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2 style="color: #333; margin-top: 0;">Hi there! 👋</h2>
            
            <p>We received a request to reset your password. Click the button below to create a new password:</p>
            
            <!-- Clickable Button -->
            <div style="text-align: center; margin: 30px 0;">
              <a href="{reset_link}" style="
                display: inline-block;
                padding: 14px 40px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 16px;
                transition: background-color 0.3s;
              ">Reset Password</a>
            </div>
            
            <!-- Fallback Text Link -->
            <p style="color: #666; font-size: 13px; border-top: 1px solid #e0e0e0; padding-top: 15px;">
              Or copy and paste this link in your browser:
            </p>
            <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 3px; font-family: monospace; font-size: 12px;">
              {reset_link}
            </p>
            
            <!-- Warning -->
            <div style="background-color: #fffbea; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0; border-radius: 3px;">
              <p style="margin: 0; color: #856404; font-size: 13px;">
                <strong>⏰ This link expires in 10 minutes.</strong><br>
                If you didn't request a password reset, you can safely ignore this email.
              </p>
            </div>
          </div>
          
          <!-- Footer -->
          <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
            <p style="margin: 0;">© 2026 Azaniah. All rights reserved.</p>
            <p style="margin: 5px 0 0 0;">Questions? Contact support@azaniah.com</p>
          </div>
        </div>
      </body>
    </html>
    """

    return send_email(user_email, subject, message, is_html=True)