import os
import json
import logging
from datetime import datetime

from app import db
from models import Email, Category, Rule

# Import OpenAI API
from openai import OpenAI

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)

def categorize_uncategorized_emails(limit=100):
    """
    Use OpenAI to categorize emails that don't have categories assigned.
    
    Args:
        limit: Maximum number of emails to process at once
        
    Returns:
        Dict with results
    """
    try:
        # Find emails without categories
        uncategorized_emails = Email.query.filter(
            ~Email.categories.any()
        ).order_by(Email.date_sent.desc()).limit(limit).all()
        
        if not uncategorized_emails:
            return {"success": True, "message": "No uncategorized emails to process", "categorized": 0}
        
        # Get existing categories
        existing_categories = Category.query.all()
        category_names = [c.name for c in existing_categories]
        
        categorized_count = 0
        
        # Process emails in batches to avoid too large requests
        batch_size = 10
        for i in range(0, len(uncategorized_emails), batch_size):
            batch = uncategorized_emails[i:i+batch_size]
            
            # Prepare email data for the model
            email_data = []
            for email in batch:
                email_data.append({
                    "id": email.id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "date": email.date_sent.isoformat() if email.date_sent else None
                })
            
            # Call OpenAI API to categorize emails
            categories = categorize_emails_with_ai(email_data, category_names)
            
            # Process results
            for email_id, assigned_categories in categories.items():
                email = next((e for e in batch if e.id == email_id), None)
                if not email:
                    continue
                
                # Assign categories
                for category_name in assigned_categories:
                    category = next((c for c in existing_categories if c.name == category_name), None)
                    if not category:
                        # Create new category if it doesn't exist
                        category = Category(name=category_name)
                        db.session.add(category)
                        existing_categories.append(category)
                    
                    email.categories.append(category)
                    category.assigned_count += 1
                
                categorized_count += 1
            
            # Commit after each batch
            db.session.commit()
        
        return {
            "success": True, 
            "message": f"Categorized {categorized_count} emails", 
            "categorized": categorized_count
        }
        
    except Exception as e:
        logger.error(f"Error categorizing emails: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

def categorize_emails_with_ai(email_data, existing_categories):
    """
    Call OpenAI API to categorize a batch of emails.
    
    Args:
        email_data: List of email data dictionaries
        existing_categories: List of existing category names
        
    Returns:
        Dict mapping email IDs to assigned categories
    """
    try:
        # Create system prompt
        system_prompt = (
            "You are an AI email categorization expert. Your task is to assign appropriate categories "
            "to each email based on the subject, sender, and other available information. "
            f"Here are the existing categories: {existing_categories}. "
            "You can use these categories or suggest new ones if needed. "
            "For each email, provide 1-3 relevant categories."
        )
        
        # Create user prompt with email data
        user_prompt = (
            "Please categorize the following emails. For each email, provide the email ID and "
            "a list of 1-3 relevant categories. Return your response as a JSON object where keys are "
            "email IDs and values are arrays of category names. Example format: "
            '{"email_id_1": ["Category1", "Category2"], "email_id_2": ["Category3"]}\n\n'
            f"Emails to categorize: {json.dumps(email_data, indent=2)}"
        )
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3  # Lower temperature for more consistent results
        )
        
        # Parse response
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        return {}

def suggest_rules(limit=5):
    """
    Use OpenAI to suggest email categorization rules based on existing patterns.
    
    Args:
        limit: Maximum number of rules to suggest
        
    Returns:
        Dict with results
    """
    try:
        # Get emails with categories for pattern analysis
        categorized_emails = db.session.query(Email).filter(
            Email.categories.any()
        ).order_by(Email.date_sent.desc()).limit(100).all()
        
        if not categorized_emails:
            return {"success": True, "message": "No categorized emails to analyze", "rules": []}
        
        # Prepare email data for the model
        email_data = []
        for email in categorized_emails:
            email_data.append({
                "subject": email.subject,
                "sender": email.sender,
                "categories": [c.name for c in email.categories]
            })
        
        # Call OpenAI API to suggest rules
        suggested_rules = suggest_rules_with_ai(email_data, limit)
        
        # Create new rules in the database
        created_rules = []
        for rule_data in suggested_rules:
            # Check if similar rule already exists
            existing_rule = Rule.query.filter_by(
                type=f"a:{rule_data['type']}",
                targets=json.dumps(rule_data['targets'])
            ).first()
            
            if not existing_rule:
                # Create new rule
                new_rule = Rule(
                    type=f"a:{rule_data['type']}",  # Prefix with a: for AI-assigned
                    targets=json.dumps(rule_data['targets']),
                    parameters=json.dumps(rule_data['parameters']),
                    results=json.dumps(rule_data['results'])
                )
                db.session.add(new_rule)
                created_rules.append(rule_data)
        
        db.session.commit()
        
        return {
            "success": True,
            "message": f"Created {len(created_rules)} new rules",
            "rules": created_rules
        }
        
    except Exception as e:
        logger.error(f"Error suggesting rules: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}", "rules": []}

def suggest_rules_with_ai(email_data, limit=5):
    """
    Call OpenAI API to suggest email categorization rules based on patterns.
    
    Args:
        email_data: List of email data dictionaries with categories
        limit: Maximum number of rules to suggest
        
    Returns:
        List of suggested rule dictionaries
    """
    try:
        # Create system prompt
        system_prompt = (
            "You are an AI email rule generation expert. Your task is to analyze patterns in "
            "categorized emails and suggest rules for automatic categorization. "
            "Rules can be based on sender email, domain, subject keywords, or other patterns. "
            "For each rule, provide a type (sender, domain, subject, keyword), targets, parameters, "
            "and the resulting category assignments."
        )
        
        # Create user prompt with email data
        user_prompt = (
            f"Please analyze these {len(email_data)} categorized emails and suggest up to {limit} rules "
            "for automatic categorization. Look for patterns in how emails are categorized based on "
            "sender addresses, domains, subject lines, etc. Return your suggestions as a JSON array of rule objects.\n\n"
            "Each rule should have:\n"
            "- type: The rule type (sender, domain, subject, keyword)\n"
            "- targets: What the rule matches against (email address, domain name, etc.)\n"
            "- parameters: Any additional parameters for matching\n"
            "- results: The categories to assign when the rule matches\n\n"
            "Example format:\n"
            '[{"type": "sender", "targets": ["example@company.com"], "parameters": {}, "results": ["Work", "Important"]}, '
            '{"type": "domain", "targets": ["newsletter.com"], "parameters": {}, "results": ["Newsletter"]}]\n\n'
            f"Email data to analyze: {json.dumps(email_data, indent=2)}"
        )
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.5
        )
        
        # Parse response
        result = json.loads(response.choices[0].message.content)
        return result.get("rules", []) if isinstance(result, dict) else result
        
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        return []

def analyze_email_content(email_id):
    """
    Use OpenAI to analyze the content of an email and extract important information.
    
    Args:
        email_id: ID of the email to analyze
        
    Returns:
        Dict with extracted information
    """
    from models import Email
    from storage import load_email_body
    
    try:
        # Get email
        email = Email.query.get(email_id)
        if not email:
            return {"success": False, "message": "Email not found"}
        
        # Load email body
        body_content = load_email_body(email.body_id, email.format)
        if not body_content:
            return {"success": False, "message": "Email body not found"}
        
        # Prepare email data
        email_data = {
            "subject": email.subject,
            "sender": email.sender,
            "date": email.date_sent.isoformat() if email.date_sent else None,
            "body": body_content
        }
        
        # Call OpenAI API to analyze email
        analysis = analyze_email_with_ai(email_data)
        
        return {
            "success": True,
            "message": "Email analyzed successfully",
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing email: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

def analyze_email_with_ai(email_data):
    """
    Call OpenAI API to analyze an email and extract important information.
    
    Args:
        email_data: Dict with email data
        
    Returns:
        Dict with analysis results
    """
    try:
        # Create system prompt
        system_prompt = (
            "You are an AI email analysis expert. Your task is to extract important information "
            "from an email, including key points, action items, deadlines, contacts mentioned, "
            "and any other relevant information. Format your response as a structured JSON object."
        )
        
        # Create user prompt with email data
        user_prompt = (
            "Please analyze this email and extract the following information:\n"
            "- key_points: Main points of the email\n"
            "- action_items: Any tasks or actions mentioned\n"
            "- deadlines: Any deadlines or dates mentioned\n"
            "- contacts: Any people or organizations mentioned\n"
            "- sentiment: The overall tone of the email (positive, neutral, negative)\n"
            "- importance: Estimated importance (high, medium, low)\n\n"
            f"Email subject: {email_data['subject']}\n"
            f"From: {email_data['sender']}\n"
            f"Date: {email_data['date']}\n\n"
            f"Body: {email_data['body']}"
        )
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        # Parse response
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        return {}
