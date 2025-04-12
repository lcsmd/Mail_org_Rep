import os
import logging
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

# Base directory for email storage
STORAGE_DIR = Path("./email_storage")

# Subdirectories
EMAIL_DIR = STORAGE_DIR / "emails"
ATTACHMENT_DIR = STORAGE_DIR / "attachments"
HTML_OBJ_DIR = STORAGE_DIR / "html-obj"
BODY_DIR = STORAGE_DIR / "bodies"
DISCLAIMER_DIR = STORAGE_DIR / "disclaimers"
THREAD_DIR = STORAGE_DIR / "threads"
GROUP_DIR = STORAGE_DIR / "groups"
RULE_DIR = STORAGE_DIR / "rules"
CATEGORY_DIR = STORAGE_DIR / "categories"

def initialize_storage():
    """Create the directory structure for email storage."""
    try:
        # Create main directories if they don't exist
        for directory in [
            STORAGE_DIR,
            EMAIL_DIR,
            ATTACHMENT_DIR,
            HTML_OBJ_DIR,
            BODY_DIR,
            DISCLAIMER_DIR,
            THREAD_DIR,
            GROUP_DIR,
            RULE_DIR,
            CATEGORY_DIR
        ]:
            directory.mkdir(exist_ok=True, parents=True)
        
        logger.info("Storage directories initialized")
        return True
    
    except Exception as e:
        logger.error(f"Error initializing storage: {str(e)}")
        return False

def save_email_body(body_id, content, format_type):
    """Save email body content to a file."""
    try:
        # Determine file extension based on format
        extension = ".hbod" if format_type == "html" else ".bod"
        
        # Create file path
        file_path = BODY_DIR / f"{body_id}{extension}"
        
        # Save content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.debug(f"Saved body {body_id} to {file_path}")
        return str(file_path)
    
    except Exception as e:
        logger.error(f"Error saving body {body_id}: {str(e)}")
        return None

def load_email_body(body_id, format_type):
    """Load email body content from a file."""
    try:
        # Determine file extension based on format
        extension = ".hbod" if format_type == "html" else ".bod"
        
        # Create file path
        file_path = BODY_DIR / f"{body_id}{extension}"
        
        # Check if file exists
        if not file_path.exists():
            logger.warning(f"Body file not found: {file_path}")
            return None
        
        # Load content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return content
    
    except Exception as e:
        logger.error(f"Error loading body {body_id}: {str(e)}")
        return None

def save_attachment(attachment_id, content):
    """Save email attachment to a file."""
    try:
        # Create file path
        file_path = ATTACHMENT_DIR / attachment_id
        
        # Save content
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.debug(f"Saved attachment {attachment_id}")
        return str(file_path)
    
    except Exception as e:
        logger.error(f"Error saving attachment {attachment_id}: {str(e)}")
        return None

def load_attachment(attachment_id):
    """Load email attachment from a file."""
    try:
        # Create file path
        file_path = ATTACHMENT_DIR / attachment_id
        
        # Check if file exists
        if not file_path.exists():
            logger.warning(f"Attachment file not found: {file_path}")
            return None
        
        # Load content
        with open(file_path, "rb") as f:
            content = f.read()
        
        return content
    
    except Exception as e:
        logger.error(f"Error loading attachment {attachment_id}: {str(e)}")
        return None

def save_html_object(object_id, content, content_type):
    """Save HTML object to a file."""
    try:
        # Create file path
        file_path = HTML_OBJ_DIR / object_id
        
        # Save content
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.debug(f"Saved HTML object {object_id}")
        return str(file_path)
    
    except Exception as e:
        logger.error(f"Error saving HTML object {object_id}: {str(e)}")
        return None

def load_html_object(object_id):
    """Load HTML object from a file."""
    try:
        # Create file path
        file_path = HTML_OBJ_DIR / object_id
        
        # Check if file exists
        if not file_path.exists():
            logger.warning(f"HTML object file not found: {file_path}")
            return None
        
        # Load content
        with open(file_path, "rb") as f:
            content = f.read()
        
        return content
    
    except Exception as e:
        logger.error(f"Error loading HTML object {object_id}: {str(e)}")
        return None

def save_disclaimer(disclaimer_id, text):
    """Save disclaimer text to a file."""
    try:
        # Create file path
        file_path = DISCLAIMER_DIR / disclaimer_id
        
        # Save content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        logger.debug(f"Saved disclaimer {disclaimer_id}")
        return str(file_path)
    
    except Exception as e:
        logger.error(f"Error saving disclaimer {disclaimer_id}: {str(e)}")
        return None

def load_disclaimer(disclaimer_id):
    """Load disclaimer text from a file."""
    try:
        # Create file path
        file_path = DISCLAIMER_DIR / disclaimer_id
        
        # Check if file exists
        if not file_path.exists():
            logger.warning(f"Disclaimer file not found: {file_path}")
            return None
        
        # Load content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return content
    
    except Exception as e:
        logger.error(f"Error loading disclaimer {disclaimer_id}: {str(e)}")
        return None

def cleanup_storage():
    """Clean up storage directories (useful for testing)."""
    try:
        # Remove all storage directories
        shutil.rmtree(STORAGE_DIR)
        
        # Recreate them
        initialize_storage()
        
        logger.info("Storage directories cleaned up")
        return True
    
    except Exception as e:
        logger.error(f"Error cleaning up storage: {str(e)}")
        return False
