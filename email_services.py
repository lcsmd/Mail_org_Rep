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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replit domain for redirect URIs
replit_dev_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
replit_domain = f"https://{replit_dev_domain}" if replit_dev_domain else f"https://{os.environ.get('REPL_SLUG')}.{os.environ.get('REPL_OWNER')}.repl.co"

# Google OAuth2 constants
# First try using the new GOOGLE_OAUTH values, fall back to old GMAIL values if not available
GMAIL_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or os.environ.get("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or os.environ.get("GMAIL_CLIENT_SECRET")
GMAIL_REDIRECT_URI = f"https://{replit_dev_domain}/accounts/add/gmail" if replit_dev_domain else os.environ.get("GMAIL_REDIRECT_URI", f"{replit_domain}/accounts/add/gmail")
GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SCOPE = "https://mail.google.com/"

# Microsoft OAuth2 constants
MS_CLIENT_ID = os.environ.get("MS_CLIENT_ID")
MS_CLIENT_SECRET = os.environ.get("MS_CLIENT_SECRET")
MS_REDIRECT_URI = f"https://{replit_dev_domain}/accounts/add/exchange" if replit_dev_domain else os.environ.get("MS_REDIRECT_URI", f"{replit_domain}/accounts/add/exchange")
# For single tenant applications, we need to use the tenant-specific endpoint
# Your selection in Azure was: "Accounts in this organizational directory only (Lawrence Sullivan MD PC only - Single tenant)"
TENANT_ID = os.environ.get("MS_TENANT_ID")  # Get tenant ID from environment
MS_AUTH_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
MS_TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
# Using Microsoft Graph API to access emails
# These permissions need to be enabled in your Azure app registration
MS_SCOPE = "offline_access https://graph.microsoft.com/mail.read"

# Print configuration information for debugging
logger.info(f"GMAIL_CLIENT_ID: {GMAIL_CLIENT_ID[:10]}... (length: {len(GMAIL_CLIENT_ID)})" if GMAIL_CLIENT_ID else "GMAIL_CLIENT_ID: Not set")
logger.info(f"GMAIL_CLIENT_SECRET: {GMAIL_CLIENT_SECRET[:5]}... (length: {len(GMAIL_CLIENT_SECRET)})" if GMAIL_CLIENT_SECRET else "GMAIL_CLIENT_SECRET: Not set")
logger.info(f"GMAIL_REDIRECT_URI: {GMAIL_REDIRECT_URI}")

# Print environment variables for debugging
import os
logger.info(f"GOOGLE_OAUTH_CLIENT_ID env var: {'Set with length '+str(len(os.environ.get('GOOGLE_OAUTH_CLIENT_ID', ''))) if os.environ.get('GOOGLE_OAUTH_CLIENT_ID') else 'Not set'}")
logger.info(f"GOOGLE_OAUTH_CLIENT_SECRET env var: {'Set with length '+str(len(os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', ''))) if os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET') else 'Not set'}")

logger.info(f"MS_CLIENT_ID: {MS_CLIENT_ID[:10]}... (length: {len(MS_CLIENT_ID)})" if MS_CLIENT_ID else "MS_CLIENT_ID: Not set")
logger.info(f"MS_CLIENT_SECRET: {MS_CLIENT_SECRET[:5]}... (length: {len(MS_CLIENT_SECRET)})" if MS_CLIENT_SECRET else "MS_CLIENT_SECRET: Not set")
logger.info(f"MS_TENANT_ID: {TENANT_ID[:10]}... (length: {len(TENANT_ID)})" if TENANT_ID else "MS_TENANT_ID: Not set")
logger.info(f"MS_REDIRECT_URI: {MS_REDIRECT_URI}")
logger.info(f"MS_AUTH_URL: {MS_AUTH_URL}")

def start_gmail_oauth():
    """Start the OAuth2 flow for Gmail."""
    # Get the OAuth client ID directly from environment variable
    oauth_client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    oauth_client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    
    if not oauth_client_id or not oauth_client_secret:
        logger.warning("Google OAuth client ID and secret not configured")
        # Return a dictionary with error info instead of raising an exception
        return {"error": True, "message": "Google OAuth client ID and secret must be configured."}
    
    logger.info(f"Using direct Google OAuth Client ID: {oauth_client_id[:10]}...")
    
    auth_params = {
        "client_id": oauth_client_id,
        "redirect_uri": GMAIL_REDIRECT_URI,
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"{GMAIL_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    
    # Log the auth URL for debugging
    logger.info(f"Gmail OAuth URL: {auth_url}")
    logger.info(f"Gmail Redirect URI: {GMAIL_REDIRECT_URI}")
    
    return auth_url

def process_gmail_oauth(request):
    """Process the OAuth2 callback for Gmail."""
    try:
        # Get the OAuth client ID directly from environment variable
        oauth_client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        oauth_client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
        
        if not oauth_client_id or not oauth_client_secret:
            logger.error("Google OAuth client ID and secret not found for callback")
            return {"success": False, "message": "Google OAuth client ID and secret must be configured."}
            
        logger.info(f"Processing callback with direct Google OAuth Client ID: {oauth_client_id[:10]}...")
        
        code = request.args.get('code')
        if not code:
            return {"success": False, "message": "Authorization code not received"}
        
        # Exchange code for access token
        token_params = {
            "client_id": oauth_client_id,
            "client_secret": oauth_client_secret,
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
    # Get the OAuth client ID directly from environment variable
    oauth_client_id = os.environ.get("MS_CLIENT_ID")
    oauth_client_secret = os.environ.get("MS_CLIENT_SECRET")
    
    if not oauth_client_id or not oauth_client_secret:
        logger.warning("Microsoft client ID and secret not configured")
        # Return a dictionary with error info instead of raising an exception
        return {"error": True, "message": "Microsoft client ID and secret must be configured."}
    
    logger.info(f"Using direct Microsoft Client ID: {oauth_client_id[:10]}...")
    
    auth_params = {
        "client_id": oauth_client_id,
        "redirect_uri": MS_REDIRECT_URI,
        "response_type": "code",
        "scope": MS_SCOPE,
        "response_mode": "query"
    }
    
    auth_url = f"{MS_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    
    # Log the auth URL for debugging
    logger.info(f"Exchange OAuth URL: {auth_url}")
    logger.info(f"Redirect URI: {MS_REDIRECT_URI}")
    
    return auth_url

def process_exchange_oauth(request):
    """Process the OAuth2 callback for Exchange Online."""
    try:
        # Get the OAuth client ID directly from environment variable
        oauth_client_id = os.environ.get("MS_CLIENT_ID")
        oauth_client_secret = os.environ.get("MS_CLIENT_SECRET")
        
        if not oauth_client_id or not oauth_client_secret:
            logger.error("Microsoft client ID and secret not found for callback")
            return {"success": False, "message": "Microsoft client ID and secret must be configured."}
            
        # Log the request URL and args for debugging
        logger.info(f"Processing Exchange OAuth callback. Request URL: {request.url}")
        logger.info(f"Request args: {request.args}")
        logger.info(f"Processing callback with direct Microsoft Client ID: {oauth_client_id[:10]}...")
        
        code = request.args.get('code')
        if not code:
            logger.error("No authorization code received in the request")
            return {"success": False, "message": "Authorization code not received"}
        
        # Exchange code for access token
        token_params = {
            "client_id": oauth_client_id,
            "client_secret": oauth_client_secret,
            "code": code,
            "redirect_uri": MS_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        logger.info(f"Exchanging code for token with params: {token_params}")
        
        response = requests.post(MS_TOKEN_URL, data=token_params)
        if response.status_code != 200:
            logger.error(f"Token exchange failed. Status: {response.status_code}, Response: {response.text}")
            return {"success": False, "message": f"Token exchange failed: {response.text}"}
        
        token_data = response.json()
        logger.info("Successfully exchanged code for token")
        
        # Get user email
        logger.info("Getting user email from Microsoft Graph API")
        user_email = get_exchange_user_email(token_data["access_token"])
        logger.info(f"User email: {user_email}")
        
        # Check if account already exists
        existing_account = EmailAccount.query.filter_by(email=user_email).first()
        if existing_account:
            logger.info(f"Updating existing account for {user_email}")
            # Update tokens
            existing_account.access_token = token_data["access_token"]
            existing_account.refresh_token = token_data.get("refresh_token", existing_account.refresh_token)
            existing_account.token_expiry = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            db.session.commit()
            return {"success": True, "message": f"Updated access for {user_email}"}
        
        # Create new account
        logger.info(f"Creating new account for {user_email}")
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
        logger.info(f"Successfully added Exchange account: {user_email}")
        
        return {"success": True, "message": f"Added Exchange account: {user_email}"}
    
    except Exception as e:
        logger.error(f"Exchange OAuth error: {str(e)}")
        import traceback
        logger.error(f"Exchange OAuth error traceback: {traceback.format_exc()}")
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
        # Get the OAuth client ID directly from environment variable
        oauth_client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        oauth_client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
        
        if not oauth_client_id or not oauth_client_secret:
            logger.error("Google OAuth client ID and secret not found for refresh")
            return False
            
        if not account.refresh_token:
            logger.error(f"No refresh token for account {account.email}")
            return False
        
        logger.info(f"Refreshing token with direct Google OAuth Client ID: {oauth_client_id[:10]}...")
        
        token_params = {
            "client_id": oauth_client_id,
            "client_secret": oauth_client_secret,
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
        # Get the OAuth client ID directly from environment variable
        oauth_client_id = os.environ.get("MS_CLIENT_ID")
        oauth_client_secret = os.environ.get("MS_CLIENT_SECRET")
        
        if not oauth_client_id or not oauth_client_secret:
            logger.error("Microsoft client ID and secret not found for refresh")
            return False
            
        if not account.refresh_token:
            logger.error(f"No refresh token for account {account.email}")
            return False
        
        logger.info(f"Refreshing token with direct Microsoft Client ID: {oauth_client_id[:10]}...")
        
        token_params = {
            "client_id": oauth_client_id,
            "client_secret": oauth_client_secret,
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
    """Fetch emails from Exchange Online using Microsoft Graph API."""
    emails = []
    
    try:
        # Check if token needs refresh
        if account.token_expiry and account.token_expiry < datetime.utcnow():
            if not refresh_exchange_token(account):
                logger.error(f"Failed to refresh token for {account.email}")
                return emails
        
        logger.info(f"Fetching emails for {account.email} using Microsoft Graph API")
        
        # Get last sync time or default to last week
        last_sync = account.last_sync or (datetime.utcnow() - timedelta(days=7))
        
        # Format date for Graph API (ISO 8601)
        date_str = last_sync.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Prepare the Graph API request
        headers = {"Authorization": f"Bearer {account.access_token}"}
        
        # Query for messages in the inbox, received after last sync
        query_params = {
            "$filter": f"receivedDateTime gt {date_str}",
            "$top": str(max_emails),
            "$orderby": "receivedDateTime desc"
        }
        
        # Make the request to Graph API
        url = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
        response = requests.get(url, headers=headers, params=query_params)
        
        if response.status_code != 200:
            logger.error(f"Error fetching emails: {response.status_code} - {response.text}")
            return emails
        
        # Process the email data
        mail_data = response.json()
        logger.info(f"Received {len(mail_data.get('value', []))} emails from Graph API")
        
        for msg in mail_data.get('value', []):
            try:
                # Instead of trying to fetch MIME content, we'll construct our own email object
                # from the Graph API data
                
                # Extract message details
                message_id = msg.get('id', '')
                subject = msg.get('subject', '(No Subject)')
                sender = msg.get('from', {}).get('emailAddress', {}).get('address', '')
                sender_name = msg.get('from', {}).get('emailAddress', {}).get('name', '')
                if sender_name:
                    sender = f"{sender_name} <{sender}>"
                    
                to_recipients = [r.get('emailAddress', {}).get('address', '') for r in msg.get('toRecipients', [])]
                cc_recipients = [r.get('emailAddress', {}).get('address', '') for r in msg.get('ccRecipients', [])]
                
                # Get the received date
                received_date = msg.get('receivedDateTime', '')
                
                # Get the body of the message
                body_content = msg.get('body', {}).get('content', '')
                body_type = msg.get('body', {}).get('contentType', 'text')
                
                # Create an RFC822 format email
                from email.message import EmailMessage
                message = EmailMessage()
                message['Message-ID'] = f"<{message_id}@microsoft.exchange>"
                message['Subject'] = subject
                message['From'] = sender
                message['To'] = ', '.join(to_recipients)
                if cc_recipients:
                    message['Cc'] = ', '.join(cc_recipients)
                message['Date'] = received_date
                
                # Set the content
                if body_type == 'html':
                    message.add_alternative(body_content, subtype='html')
                else:
                    message.set_content(body_content)
                
                # Convert to bytes
                raw_email = message.as_bytes()
                emails.append(raw_email)
                
                logger.info(f"Processed email: {subject}")
            except Exception as msg_error:
                logger.error(f"Error processing message {msg.get('id', 'unknown')}: {str(msg_error)}")
                continue
        
        logger.info(f"Successfully processed {len(emails)} emails for {account.email}")
    
    except Exception as e:
        logger.error(f"Error fetching Exchange emails: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    return emails
