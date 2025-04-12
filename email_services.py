import os
import logging
import imaplib
import email
import base64
import json
from datetime import datetime, timedelta
import urllib.parse
import requests

from app import db
from models import EmailAccount

logger = logging.getLogger(__name__)

# Google OAuth2 constants
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET")
GMAIL_REDIRECT_URI = os.environ.get("GMAIL_REDIRECT_URI", "http://localhost:5000/accounts/add/gmail")
GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SCOPE = "https://mail.google.com/"

# Microsoft OAuth2 constants
MS_CLIENT_ID = os.environ.get("MS_CLIENT_ID")
MS_CLIENT_SECRET = os.environ.get("MS_CLIENT_SECRET")
MS_REDIRECT_URI = os.environ.get("MS_REDIRECT_URI", "http://localhost:5000/accounts/add/exchange")
MS_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MS_SCOPE = "https://outlook.office.com/IMAP.AccessAsUser.All https://outlook.office.com/mail.read"

def start_gmail_oauth():
    """Start the OAuth2 flow for Gmail."""
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET:
        logger.warning("Gmail client ID and secret not configured")
        # Return a dictionary with error info instead of raising an exception
        return {"error": True, "message": "Gmail client ID and secret must be configured. Please set the GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables."}
    
    auth_params = {
        "client_id": GMAIL_CLIENT_ID,
        "redirect_uri": GMAIL_REDIRECT_URI,
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"{GMAIL_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    return auth_url

def process_gmail_oauth(request):
    """Process the OAuth2 callback for Gmail."""
    try:
        code = request.args.get('code')
        if not code:
            return {"success": False, "message": "Authorization code not received"}
        
        # Exchange code for access token
        token_params = {
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GMAIL_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(GMAIL_TOKEN_URL, data=token_params)
        if response.status_code != 200:
            return {"success": False, "message": f"Token exchange failed: {response.text}"}
        
        token_data = response.json()
        
        # Get user email
        user_email = get_gmail_user_email(token_data["access_token"])
        
        # Check if account already exists
        existing_account = EmailAccount.query.filter_by(email=user_email).first()
        if existing_account:
            # Update tokens
            existing_account.access_token = token_data["access_token"]
            existing_account.refresh_token = token_data.get("refresh_token", existing_account.refresh_token)
            existing_account.token_expiry = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            db.session.commit()
            return {"success": True, "message": f"Updated access for {user_email}"}
        
        # Create new account
        new_account = EmailAccount(
            email=user_email,
            account_type="gmail",
            display_name=user_email,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expiry=datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        )
        
        db.session.add(new_account)
        db.session.commit()
        
        return {"success": True, "message": f"Added Gmail account: {user_email}"}
    
    except Exception as e:
        logger.error(f"Gmail OAuth error: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

def get_gmail_user_email(access_token):
    """Get user email from Gmail API."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://www.googleapis.com/gmail/v1/users/me/profile", headers=headers)
    
    if response.status_code != 200:
        raise ValueError(f"Failed to get user email: {response.text}")
    
    return response.json()["emailAddress"]

def start_exchange_oauth():
    """Start the OAuth2 flow for Exchange Online."""
    if not MS_CLIENT_ID or not MS_CLIENT_SECRET:
        logger.warning("Microsoft client ID and secret not configured")
        # Return a dictionary with error info instead of raising an exception
        return {"error": True, "message": "Microsoft client ID and secret must be configured. Please set the MS_CLIENT_ID and MS_CLIENT_SECRET environment variables."}
    
    auth_params = {
        "client_id": MS_CLIENT_ID,
        "redirect_uri": MS_REDIRECT_URI,
        "response_type": "code",
        "scope": MS_SCOPE,
        "response_mode": "query"
    }
    
    auth_url = f"{MS_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    return auth_url

def process_exchange_oauth(request):
    """Process the OAuth2 callback for Exchange Online."""
    try:
        code = request.args.get('code')
        if not code:
            return {"success": False, "message": "Authorization code not received"}
        
        # Exchange code for access token
        token_params = {
            "client_id": MS_CLIENT_ID,
            "client_secret": MS_CLIENT_SECRET,
            "code": code,
            "redirect_uri": MS_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(MS_TOKEN_URL, data=token_params)
        if response.status_code != 200:
            return {"success": False, "message": f"Token exchange failed: {response.text}"}
        
        token_data = response.json()
        
        # Get user email
        user_email = get_exchange_user_email(token_data["access_token"])
        
        # Check if account already exists
        existing_account = EmailAccount.query.filter_by(email=user_email).first()
        if existing_account:
            # Update tokens
            existing_account.access_token = token_data["access_token"]
            existing_account.refresh_token = token_data.get("refresh_token", existing_account.refresh_token)
            existing_account.token_expiry = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            db.session.commit()
            return {"success": True, "message": f"Updated access for {user_email}"}
        
        # Create new account
        new_account = EmailAccount(
            email=user_email,
            account_type="exchange",
            display_name=user_email,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expiry=datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        )
        
        db.session.add(new_account)
        db.session.commit()
        
        return {"success": True, "message": f"Added Exchange account: {user_email}"}
    
    except Exception as e:
        logger.error(f"Exchange OAuth error: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

def get_exchange_user_email(access_token):
    """Get user email from Microsoft Graph API."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    
    if response.status_code != 200:
        raise ValueError(f"Failed to get user email: {response.text}")
    
    return response.json()["mail"] or response.json()["userPrincipalName"]

def refresh_gmail_token(account):
    """Refresh the OAuth2 token for a Gmail account."""
    try:
        if not account.refresh_token:
            logger.error(f"No refresh token for account {account.email}")
            return False
        
        token_params = {
            "client_id": GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "refresh_token": account.refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(GMAIL_TOKEN_URL, data=token_params)
        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            return False
        
        token_data = response.json()
        
        account.access_token = token_data["access_token"]
        account.token_expiry = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        db.session.commit()
        
        return True
    
    except Exception as e:
        logger.error(f"Error refreshing Gmail token: {str(e)}")
        return False

def refresh_exchange_token(account):
    """Refresh the OAuth2 token for an Exchange account."""
    try:
        if not account.refresh_token:
            logger.error(f"No refresh token for account {account.email}")
            return False
        
        token_params = {
            "client_id": MS_CLIENT_ID,
            "client_secret": MS_CLIENT_SECRET,
            "refresh_token": account.refresh_token,
            "grant_type": "refresh_token",
            "scope": MS_SCOPE
        }
        
        response = requests.post(MS_TOKEN_URL, data=token_params)
        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            return False
        
        token_data = response.json()
        
        account.access_token = token_data["access_token"]
        account.token_expiry = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        db.session.commit()
        
        return True
    
    except Exception as e:
        logger.error(f"Error refreshing Exchange token: {str(e)}")
        return False

def fetch_emails_gmail(account, max_emails=50):
    """Fetch emails from Gmail using IMAP."""
    emails = []
    
    try:
        # Check if token needs refresh
        if account.token_expiry and account.token_expiry < datetime.utcnow():
            if not refresh_gmail_token(account):
                logger.error(f"Failed to refresh token for {account.email}")
                return emails
        
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        
        # Authenticate with OAuth2
        auth_string = f'user={account.email}\1auth=Bearer {account.access_token}\1\1'
        mail.authenticate('XOAUTH2', lambda x: auth_string)
        
        # Select inbox
        mail.select('INBOX')
        
        # Get last sync time or default to last week
        last_sync = account.last_sync or (datetime.utcnow() - timedelta(days=7))
        
        # Search for emails since last sync
        date_str = last_sync.strftime("%d-%b-%Y")
        result, data = mail.search(None, f'(SINCE {date_str})')
        
        if result != 'OK':
            logger.error(f"Error searching emails: {result}")
            return emails
        
        # Get email IDs
        email_ids = data[0].split()
        
        # Limit number of emails to process
        email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids
        
        # Fetch emails
        for e_id in reversed(email_ids):  # Process newest first
            result, data = mail.fetch(e_id, '(RFC822)')
            if result != 'OK':
                logger.error(f"Error fetching email {e_id}: {result}")
                continue
            
            raw_email = data[0][1]
            emails.append(raw_email)
        
        mail.logout()
    
    except Exception as e:
        logger.error(f"Error fetching Gmail emails: {str(e)}")
    
    return emails

def fetch_emails_exchange(account, max_emails=50):
    """Fetch emails from Exchange Online using IMAP."""
    emails = []
    
    try:
        # Check if token needs refresh
        if account.token_expiry and account.token_expiry < datetime.utcnow():
            if not refresh_exchange_token(account):
                logger.error(f"Failed to refresh token for {account.email}")
                return emails
        
        # Connect to Exchange Online IMAP
        mail = imaplib.IMAP4_SSL('outlook.office365.com')
        
        # Authenticate with OAuth2
        auth_string = f'user={account.email}\1auth=Bearer {account.access_token}\1\1'
        mail.authenticate('XOAUTH2', lambda x: auth_string)
        
        # Select inbox
        mail.select('INBOX')
        
        # Get last sync time or default to last week
        last_sync = account.last_sync or (datetime.utcnow() - timedelta(days=7))
        
        # Search for emails since last sync
        date_str = last_sync.strftime("%d-%b-%Y")
        result, data = mail.search(None, f'(SINCE {date_str})')
        
        if result != 'OK':
            logger.error(f"Error searching emails: {result}")
            return emails
        
        # Get email IDs
        email_ids = data[0].split()
        
        # Limit number of emails to process
        email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids
        
        # Fetch emails
        for e_id in reversed(email_ids):  # Process newest first
            result, data = mail.fetch(e_id, '(RFC822)')
            if result != 'OK':
                logger.error(f"Error fetching email {e_id}: {result}")
                continue
            
            raw_email = data[0][1]
            emails.append(raw_email)
        
        mail.logout()
    
    except Exception as e:
        logger.error(f"Error fetching Exchange emails: {str(e)}")
    
    return emails
