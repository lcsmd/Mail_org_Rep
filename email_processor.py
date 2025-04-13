import os
import json
import hashlib
import logging
import re
import email
from email import policy
from email.parser import BytesParser
from datetime import datetime, timedelta
from io import BytesIO
from bs4 import BeautifulSoup

from app import db
from models import EmailAccount, Email, Body, Attachment, HTMLObject, Disclaimer, Thread, Contact, Domain
from storage import save_email_body, save_attachment, save_html_object
from email_services import fetch_emails_gmail, fetch_emails_exchange

logger = logging.getLogger(__name__)

def process_account_emails(account, max_emails=50):
    """Fetch and process new emails from a specific account."""
    try:
        processed_count = 0
        
        # Fetch emails based on account type
        if account.account_type == 'gmail':
            emails = fetch_emails_gmail(account, max_emails)
        elif account.account_type == 'exchange':
            emails = fetch_emails_exchange(account, max_emails)
        else:
            logger.warning(f"Unknown account type: {account.account_type}")
            return {"success": False, "message": f"Unknown account type: {account.account_type}"}
        
        # Process each email
        for email_data in emails:
            if process_email(email_data, account):
                processed_count += 1
        
        return {
            "success": True,
            "message": f"Processed {processed_count} new emails for {account.email}",
            "processed": processed_count
        }
    except Exception as e:
        logger.error(f"Error processing emails for {account.email}: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

def process_new_emails():
    """Fetch and process new emails from all configured accounts."""
    try:
        accounts = EmailAccount.query.all()
        if not accounts:
            return {"success": False, "message": "No email accounts configured"}
        
        processed_count = 0
        
        for account in accounts:
            result = process_account_emails(account)
            if result["success"]:
                processed_count += result.get("processed", 0)
            
            # Update last sync time
            account.last_sync = datetime.utcnow()
            db.session.commit()
        
        return {
            "success": True,
            "message": f"Processed {processed_count} new emails",
            "processed": processed_count
        }
    
    except Exception as e:
        logger.error(f"Error processing emails: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

def process_email(email_data, account):
    """Process a single email message."""
    try:
        # Parse the email message
        msg = BytesParser(policy=policy.default).parsebytes(email_data)
        
        # Check if email already exists to avoid duplicates
        message_id = msg.get('Message-ID', '')
        if message_id:
            existing = Email.query.filter_by(message_id=message_id).first()
            if existing:
                logger.info(f"Email with Message-ID {message_id} already exists, skipping")
                return False
        
        # Create new email record
        email_obj = Email(
            message_id=message_id,
            account_id=account.id,
            sender=msg.get('From', ''),
            subject=msg.get('Subject', ''),
            date_sent=parse_date(msg.get('Date', '')),
        )
        
        # Set recipients
        if msg.get('To'):
            email_obj.recipients = json.dumps(parse_addresses(msg.get('To', '')))
        
        if msg.get('Cc'):
            email_obj.cc = json.dumps(parse_addresses(msg.get('Cc', '')))
        
        if msg.get('Bcc'):
            email_obj.bcc = json.dumps(parse_addresses(msg.get('Bcc', '')))
        
        # Process body and attachments
        process_email_content(msg, email_obj)
        
        # Find or create thread
        thread = find_or_create_thread(email_obj)
        email_obj.thread_id = thread.id
        
        # Process contacts and domains
        process_contacts_and_domains(email_obj)
        
        # Save the email
        db.session.add(email_obj)
        db.session.commit()
        
        logger.info(f"Processed email: {email_obj.subject}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing individual email: {str(e)}")
        return False

def process_email_content(msg, email_obj):
    """Process the content of an email including body and attachments."""
    # Check if this is a multipart message
    if msg.is_multipart():
        # Process each part
        text_part = None
        html_part = None
        attachments = []
        
        for part in msg.iter_parts():
            content_type = part.get_content_type()
            
            if content_type == 'text/plain' and not text_part:
                text_part = part
            elif content_type == 'text/html' and not html_part:
                html_part = part
            elif part.get_filename():
                attachments.append(part)
        
        # Prefer HTML over plain text if available
        if html_part:
            process_html_body(html_part, email_obj)
        elif text_part:
            process_text_body(text_part, email_obj)
        
        # Process attachments
        for attachment_part in attachments:
            process_attachment(attachment_part, email_obj)
    
    else:
        # Not multipart, process as single part
        content_type = msg.get_content_type()
        
        if content_type == 'text/plain':
            process_text_body(msg, email_obj)
        elif content_type == 'text/html':
            process_html_body(msg, email_obj)

def process_text_body(part, email_obj):
    """Process a plain text email body."""
    # Get the text content
    text_content = part.get_content()
    
    # Remove any forwarded content and store separately
    text_content, forwarded_content = extract_forwarded_content(text_content)
    
    # Extract and separate disclaimers
    text_content, disclaimers = extract_disclaimers(text_content)
    
    # Create body record
    body = Body()
    db.session.add(body)
    db.session.flush()  # Generate ID
    
    # Save body content to file
    save_email_body(body.id, text_content, 'text')
    
    # Add disclaimers if found
    for disclaimer_text in disclaimers:
        disclaimer = find_or_create_disclaimer(disclaimer_text)
        body.disclaimers.append(disclaimer)
    
    # Set email body
    email_obj.body_id = body.id
    email_obj.format = 'text'
    
    # Process any forwarded content
    if forwarded_content:
        process_forwarded_content(forwarded_content, email_obj)

def process_html_body(part, email_obj):
    """Process an HTML email body."""
    # Get the HTML content
    html_content = part.get_content()
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract and process HTML objects (images, etc.)
    html_objects = extract_html_objects(soup)
    for obj_data in html_objects:
        html_obj = HTMLObject()
        db.session.add(html_obj)
        db.session.flush()  # Generate ID
        
        # Save object to file
        save_html_object(html_obj.id, obj_data['content'], obj_data['content_type'])
        
        # Set properties
        html_obj.content_type = obj_data['content_type']
        
        # Replace in HTML with reference
        obj_data['element']['src'] = f"[[HTML_OBJECT:{html_obj.id}]]"
        
        # Add to email
        email_obj.html_objects.append(html_obj)
    
    # Extract and separate disclaimers
    html_content, disclaimers = extract_html_disclaimers(str(soup))
    
    # Create body record
    body = Body()
    db.session.add(body)
    db.session.flush()  # Generate ID
    
    # Save body content to file
    save_email_body(body.id, html_content, 'html')
    
    # Add disclaimers if found
    for disclaimer_text in disclaimers:
        disclaimer = find_or_create_disclaimer(disclaimer_text)
        body.disclaimers.append(disclaimer)
    
    # Set email body
    email_obj.body_id = body.id
    email_obj.format = 'html'
    
    # Process any forwarded content
    forwarded_content = extract_html_forwarded_content(soup)
    if forwarded_content:
        process_forwarded_content(forwarded_content, email_obj)

def process_attachment(part, email_obj):
    """Process an email attachment."""
    filename = part.get_filename()
    content_type = part.get_content_type()
    content = part.get_payload(decode=True)
    
    # Calculate hash to check for duplicates
    content_hash = hashlib.md5(content).hexdigest()
    
    # Check if attachment already exists
    existing = Attachment.query.filter_by(id=content_hash).first()
    if existing:
        # Reuse existing attachment
        email_obj.attachments.append(existing)
        return
    
    # Create new attachment record
    attachment = Attachment(
        id=content_hash,
        filename=filename,
        content_type=content_type,
        size=len(content)
    )
    
    # Save attachment content to file
    save_attachment(attachment.id, content)
    
    # Add to database and email
    db.session.add(attachment)
    email_obj.attachments.append(attachment)

def extract_forwarded_content(text_content):
    """Extract forwarded email content from plain text."""
    # Common forwarded email patterns
    forward_patterns = [
        r'(?m)^-+\s*Forwarded message\s*-+\s*$(.*?)(?=^-+|$)',
        r'(?m)^-+\s*Original Message\s*-+\s*$(.*?)(?=^-+|$)',
        r'(?m)^From:.*?^Sent:.*?^To:.*?^Subject:.*?$(.*)'
    ]
    
    forwarded_content = None
    
    for pattern in forward_patterns:
        match = re.search(pattern, text_content, re.DOTALL)
        if match:
            forwarded_content = match.group(1).strip()
            text_content = text_content.replace(match.group(0), '').strip()
            break
    
    return text_content, forwarded_content

def extract_html_forwarded_content(soup):
    """Extract forwarded email content from HTML."""
    # Look for common forwarded email markers in divs, blockquotes, etc.
    forward_markers = [
        "Forwarded message",
        "Original Message",
        "Begin forwarded message"
    ]
    
    for marker in forward_markers:
        elements = soup.find_all(text=re.compile(marker))
        if elements:
            for element in elements:
                # Find the parent element that likely contains the forwarded message
                parent = element.parent
                while parent and parent.name not in ['div', 'blockquote', 'body']:
                    parent = parent.parent
                
                if parent and parent.name != 'body':
                    return str(parent)
    
    # Check for common forwarded email structures (like blockquotes)
    blockquotes = soup.find_all('blockquote')
    if blockquotes:
        for blockquote in blockquotes:
            if blockquote.get('class') and 'gmail_quote' in blockquote.get('class'):
                return str(blockquote)
    
    return None

def process_forwarded_content(content, parent_email):
    """Process content from a forwarded email."""
    # Simple implementation - in a real system this would be more sophisticated
    # to extract headers and content from the forwarded text
    logger.info(f"Detected forwarded content in email {parent_email.id}")

def extract_disclaimers(text_content):
    """Extract common disclaimers from text content."""
    # Common disclaimer patterns
    disclaimer_patterns = [
        r'(?m)^DISCLAIMER:.*?$(?:\n.*?$)*',
        r'(?m)^CONFIDENTIALITY NOTICE:.*?$(?:\n.*?$)*',
        r'(?m)^LEGAL DISCLAIMER:.*?$(?:\n.*?$)*',
        r'(?m)^This email and any files.*?$(?:\n.*?$)*',
        r'(?m)^The information contained in this.*?$(?:\n.*?$)*'
    ]
    
    disclaimers = []
    
    for pattern in disclaimer_patterns:
        matches = re.finditer(pattern, text_content, re.MULTILINE)
        for match in matches:
            disclaimer_text = match.group(0).strip()
            disclaimers.append(disclaimer_text)
            text_content = text_content.replace(disclaimer_text, '').strip()
    
    return text_content, disclaimers

def extract_html_disclaimers(html_content):
    """Extract common disclaimers from HTML content."""
    # Common disclaimer patterns
    disclaimer_patterns = [
        r'<div[^>]*>\s*DISCLAIMER:.*?</div>',
        r'<div[^>]*>\s*CONFIDENTIALITY NOTICE:.*?</div>',
        r'<div[^>]*>\s*LEGAL DISCLAIMER:.*?</div>',
        r'<div[^>]*>\s*This email and any files.*?</div>',
        r'<div[^>]*>\s*The information contained in this.*?</div>'
    ]
    
    disclaimers = []
    
    for pattern in disclaimer_patterns:
        matches = re.finditer(pattern, html_content, re.DOTALL)
        for match in matches:
            disclaimer_html = match.group(0).strip()
            # Convert HTML to plain text for storage
            soup = BeautifulSoup(disclaimer_html, 'html.parser')
            disclaimer_text = soup.get_text().strip()
            disclaimers.append(disclaimer_text)
            html_content = html_content.replace(disclaimer_html, '').strip()
    
    return html_content, disclaimers

def extract_html_objects(soup):
    """Extract images and other embedded objects from HTML."""
    objects = []
    
    # Extract images
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src.startswith('data:'):
            # Extract base64 encoded image
            try:
                content_type = src.split(';')[0].split(':')[1]
                base64_data = src.split(',')[1]
                import base64
                content = base64.b64decode(base64_data)
                objects.append({
                    'element': img,
                    'content': content,
                    'content_type': content_type
                })
            except:
                logger.warning("Failed to extract base64 image data")
    
    return objects

def find_or_create_disclaimer(text):
    """Find existing disclaimer or create a new one."""
    # Calculate hash for deduplication
    text_hash = hashlib.md5(text.encode()).hexdigest()
    
    # Check if disclaimer already exists
    disclaimer = Disclaimer.query.filter_by(id=text_hash).first()
    if not disclaimer:
        # Create new disclaimer
        disclaimer = Disclaimer(id=text_hash, text=text)
        db.session.add(disclaimer)
    
    return disclaimer

def find_or_create_thread(email_obj):
    """Find existing thread or create a new one based on email subject and references."""
    # Normalize subject by removing Re:, Fwd:, etc.
    normalized_subject = normalize_subject(email_obj.subject)
    
    # Find existing thread with similar subject
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    thread = Thread.query.join(Email).filter(
        Thread.subject == normalized_subject,
        Thread.last_date > one_week_ago
    ).order_by(Thread.last_date.desc()).first()
    
    if not thread:
        # Create new thread
        thread = Thread(
            subject=normalized_subject,
            date_started=email_obj.date_sent,
            last_date=email_obj.date_sent
        )
        db.session.add(thread)
        db.session.flush()  # Generate ID
    else:
        # Update thread last date
        thread.last_date = max(thread.last_date, email_obj.date_sent)
    
    return thread

def normalize_subject(subject):
    """Normalize email subject by removing common prefixes."""
    if not subject:
        return "(No Subject)"
    
    # Remove Re:, Fwd:, etc.
    normalized = re.sub(r'^(?:Re|Fwd|Fw|FW|RE|FWD):\s*', '', subject, flags=re.IGNORECASE)
    
    # If empty after normalization, use original
    if not normalized.strip():
        return subject
    
    return normalized

def process_contacts_and_domains(email_obj):
    """Process sender and recipient addresses to update contact and domain records."""
    # Process sender
    if email_obj.sender:
        sender_email = extract_email(email_obj.sender)
        if sender_email:
            contact = find_or_create_contact(sender_email)
            contact.sent_count += 1
            
            domain = extract_domain(sender_email)
            if domain:
                domain_obj = find_or_create_domain(domain)
                domain_obj.sent_count += 1
    
    # Process recipients
    if email_obj.recipients:
        recipients = json.loads(email_obj.recipients)
        for recipient in recipients:
            recipient_email = extract_email(recipient)
            if recipient_email:
                contact = find_or_create_contact(recipient_email)
                contact.received_count += 1
                
                domain = extract_domain(recipient_email)
                if domain:
                    domain_obj = find_or_create_domain(domain)
                    domain_obj.received_count += 1

def find_or_create_contact(email_address):
    """Find existing contact or create a new one."""
    contact = Contact.query.filter_by(email=email_address).first()
    if not contact:
        # Try to extract name parts from email
        name_parts = extract_name_from_email(email_address)
        
        contact = Contact(
            email=email_address,
            firstname=name_parts.get('firstname', ''),
            lastname=name_parts.get('lastname', '')
        )
        db.session.add(contact)
        db.session.flush()  # Generate ID
    
    return contact

def find_or_create_domain(domain_name):
    """Find existing domain or create a new one."""
    domain = Domain.query.filter_by(email_domain=domain_name).first()
    if not domain:
        domain = Domain(email_domain=domain_name)
        db.session.add(domain)
        db.session.flush()  # Generate ID
    
    return domain

def extract_email(address_str):
    """Extract email address from a formatted email string."""
    match = re.search(r'[\w\.-]+@[\w\.-]+', address_str)
    if match:
        return match.group(0).lower()
    return None

def extract_domain(email):
    """Extract domain from email address."""
    parts = email.split('@')
    if len(parts) == 2:
        return parts[1].lower()
    return None

def extract_name_from_email(email_address):
    """Extract first and last name from email address if possible."""
    result = {}
    
    # First try to split local part by . or _
    local_part = email_address.split('@')[0]
    
    if '.' in local_part:
        parts = local_part.split('.')
        if len(parts) >= 2:
            result['firstname'] = parts[0].capitalize()
            result['lastname'] = parts[1].capitalize()
    elif '_' in local_part:
        parts = local_part.split('_')
        if len(parts) >= 2:
            result['firstname'] = parts[0].capitalize()
            result['lastname'] = parts[1].capitalize()
    
    return result

def parse_addresses(address_field):
    """Parse an email address field into a list of addresses."""
    if not address_field:
        return []
    
    # Simple split by comma, a more robust solution would use email.utils.parseaddr
    addresses = [addr.strip() for addr in address_field.split(',')]
    return addresses

def parse_date(date_string):
    """Parse email date string into datetime object."""
    if not date_string:
        return datetime.utcnow()
    
    try:
        # Use email's parsedate_to_datetime function
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_string)
    except:
        # Fallback to current time if parsing fails
        logger.warning(f"Failed to parse date: {date_string}")
        return datetime.utcnow()
