import os
import logging
from flask import Flask, session, redirect, url_for, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize Flask app and SQLAlchemy
db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Set secret key from environment variable
app.secret_key = os.environ.get("SESSION_SECRET", "development-secret-key")

# Configure proxy fix for URL generation
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure PostgreSQL database - ensuring DATABASE_URL is properly set
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set.")
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
print(f"Using database URL: {database_url}")

# Initialize the database with the app
db.init_app(app)

# Create all tables
with app.app_context():
    # Import models here to ensure they're registered before creating tables
    import models
    db.create_all()

@app.route('/')
def index():
    # Check if there are any configured email accounts
    from models import EmailAccount
    accounts = EmailAccount.query.all()
    
    if not accounts:
        # If no accounts are configured, redirect to setup page
        return redirect(url_for('setup'))
    
    # Otherwise show the dashboard
    return render_template('index.html', accounts=accounts)

@app.route('/setup')
def setup():
    # Import the configuration to pass to the template
    import logging
    try:
        from config import current_config
        logging.info(f"Rendering setup.html with config={current_config.__dict__}")
        return render_template('setup.html', config=current_config)
    except Exception as e:
        logging.error(f"Error rendering setup page: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return f"Error rendering setup page: {str(e)}", 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    logging.error(f"Server error: {e}")
    return render_template('500.html'), 500

# Create a routes module
def register_routes(app):
    # Email account management
    @app.route('/accounts', methods=['GET'])
    def list_accounts():
        from models import EmailAccount
        from datetime import datetime
        accounts = EmailAccount.query.all()
        return render_template('accounts.html', accounts=accounts, now=datetime.utcnow())
    
    @app.route('/accounts/add/gmail', methods=['GET', 'POST'])
    def add_gmail_account():
        import logging
        
        # Debug information
        logging.info(f"Gmail OAuth Route - Method: {request.method}")
        logging.info(f"Gmail OAuth Route - URL: {request.url}")
        logging.info(f"Gmail OAuth Route - Args: {request.args}")
        
        # Check if this is the OAuth callback (has code in query string)
        if request.args.get('code'):
            # Process Gmail OAuth callback
            logging.info("Processing Gmail OAuth callback (code detected in query args)")
            from email_services import process_gmail_oauth
            result = process_gmail_oauth(request)
            if result['success']:
                logging.info(f"Gmail OAuth successful: {result['message']}")
                return redirect(url_for('list_accounts'))
            else:
                logging.error(f"Gmail OAuth error: {result['message']}")
                return render_template('error.html', message=result['message'])
        else:
            # Initiate Gmail OAuth flow
            logging.info("Initiating Gmail OAuth flow")
            from email_services import start_gmail_oauth
            result = start_gmail_oauth()
            
            # Check if we got an error instead of an auth URL
            if isinstance(result, dict) and result.get('error'):
                logging.error(f"Gmail OAuth error: {result['message']}")
                return render_template('error.html', message=result['message'])
            
            # Log the authorization URL 
            logging.info(f"Gmail OAuth redirecting to: {result}")
                
            # Redirect to the authorization URL
            return redirect(result)
    
    @app.route('/accounts/add/exchange', methods=['GET', 'POST'])
    def add_exchange_account():
        import logging
        
        # Debug information
        logging.info(f"Exchange OAuth Route - Method: {request.method}")
        logging.info(f"Exchange OAuth Route - URL: {request.url}")
        logging.info(f"Exchange OAuth Route - Args: {request.args}")
        
        # Check if this is the OAuth callback (has code in query string)
        if request.args.get('code'):
            # Process Exchange OAuth callback
            logging.info("Processing Exchange OAuth callback (code detected in query args)")
            from email_services import process_exchange_oauth
            result = process_exchange_oauth(request)
            if result['success']:
                logging.info(f"Exchange OAuth successful: {result['message']}")
                return redirect(url_for('list_accounts'))
            else:
                logging.error(f"Exchange OAuth error: {result['message']}")
                return render_template('error.html', message=result['message'])
        else:
            # Initiate Exchange OAuth flow
            logging.info("Initiating Exchange OAuth flow")
            from email_services import start_exchange_oauth
            result = start_exchange_oauth()
            
            # Check if we got an error instead of an auth URL
            if isinstance(result, dict) and result.get('error'):
                logging.error(f"Exchange OAuth error: {result['message']}")
                return render_template('error.html', message=result['message'])
            
            # Log the authorization URL 
            logging.info(f"Exchange OAuth redirecting to: {result}")
                
            # Redirect to the authorization URL
            return redirect(result)
    
    @app.route('/accounts/delete/<int:account_id>', methods=['POST'])
    def delete_account(account_id):
        from models import EmailAccount
        account = EmailAccount.query.get_or_404(account_id)
        db.session.delete(account)
        db.session.commit()
        return redirect(url_for('list_accounts'))
    
    # Email viewing routes
    @app.route('/emails', methods=['GET'])
    def list_emails():
        from models import Email
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # Get filter parameters
        category = request.args.get('category')
        sender = request.args.get('sender')
        subject = request.args.get('subject')
        
        # Build query
        query = Email.query
        if category:
            query = query.filter(Email.categories.contains(category))
        if sender:
            query = query.filter(Email.sender.ilike(f'%{sender}%'))
        if subject:
            query = query.filter(Email.subject.ilike(f'%{subject}%'))
        
        # Order by date, newest first
        emails = query.order_by(Email.date_sent.desc()).paginate(page=page, per_page=per_page)
        
        return render_template('emails.html', emails=emails)
    
    @app.route('/email/<string:email_id>', methods=['GET'])
    def view_email(email_id):
        from models import Email
        email = Email.query.get_or_404(email_id)
        
        # Load email body content
        from storage import load_email_body
        body_content = load_email_body(email.body_id, email.format)
        
        return render_template('email_view.html', email=email, body_content=body_content)
    
    @app.route('/thread/<string:thread_id>', methods=['GET'])
    def view_thread(thread_id):
        from models import Thread, Email
        thread = Thread.query.get_or_404(thread_id)
        
        # Get all emails in this thread, ordered by date
        emails = Email.query.filter(Email.thread_id == thread_id).order_by(Email.date_sent).all()
        
        return render_template('thread_view.html', thread=thread, emails=emails)
    
    # Category management
    @app.route('/categories', methods=['GET'])
    def list_categories():
        from models import Category
        categories = Category.query.all()
        return render_template('categories.html', categories=categories)
    
    @app.route('/categories/add', methods=['POST'])
    def add_category():
        from models import Category
        name = request.form.get('name')
        parent_id = request.form.get('parent_id')
        
        category = Category(name=name)
        if parent_id:
            category.parent_id = parent_id
            
        db.session.add(category)
        db.session.commit()
        
        return redirect(url_for('list_categories'))
    
    @app.route('/categories/delete/<int:category_id>', methods=['POST'])
    def delete_category(category_id):
        from models import Category
        category = Category.query.get_or_404(category_id)
        db.session.delete(category)
        db.session.commit()
        
        return redirect(url_for('list_categories'))
    
    # Rule management
    @app.route('/rules', methods=['GET'])
    def list_rules():
        from models import Rule
        rules = Rule.query.all()
        return render_template('rules.html', rules=rules)
    
    @app.route('/rules/add', methods=['POST'])
    def add_rule():
        from models import Rule
        rule_type = request.form.get('type')
        targets = request.form.get('targets')
        parameters = request.form.get('parameters')
        results = request.form.get('results')
        
        rule = Rule(
            type=rule_type,
            targets=targets,
            parameters=parameters,
            results=results
        )
        
        db.session.add(rule)
        db.session.commit()
        
        return redirect(url_for('list_rules'))
    
    @app.route('/rules/delete/<int:rule_id>', methods=['POST'])
    def delete_rule(rule_id):
        from models import Rule
        rule = Rule.query.get_or_404(rule_id)
        db.session.delete(rule)
        db.session.commit()
        
        return redirect(url_for('list_rules'))
    
    # Email processing
    @app.route('/process/refresh', methods=['POST'])
    def refresh_emails():
        from email_processor import process_new_emails
        result = process_new_emails()
        
        return jsonify({
            'success': result['success'],
            'message': result['message'],
            'processed': result.get('processed', 0)
        })
        
    @app.route('/accounts/<int:account_id>/sync', methods=['POST'])
    def sync_account(account_id):
        from models import EmailAccount
        from email_processor import process_account_emails
        from datetime import datetime
        
        account = EmailAccount.query.get_or_404(account_id)
        result = process_account_emails(account)
        
        # Update last sync time
        account.last_sync = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': result['success'],
            'message': result['message'],
            'processed': result.get('processed', 0)
        })
    
    # AI operations
    @app.route('/ai/categorize', methods=['POST'])
    def ai_categorize():
        from ai_service import categorize_uncategorized_emails
        result = categorize_uncategorized_emails()
        
        return jsonify({
            'success': result['success'],
            'message': result['message'],
            'categorized': result.get('categorized', 0)
        })
    
    @app.route('/ai/suggest-rules', methods=['POST'])
    def ai_suggest_rules():
        from ai_service import suggest_rules
        result = suggest_rules()
        
        return jsonify({
            'success': result['success'],
            'message': result['message'],
            'rules': result.get('rules', [])
        })
    
    # Search
    @app.route('/search', methods=['GET'])
    def search():
        query = request.args.get('q', '')
        if not query:
            return render_template('search.html', results=None)
        
        from models import Email
        # Simple search in email subjects and senders
        results = Email.query.filter(
            (Email.subject.contains(query)) | 
            (Email.sender.contains(query))
        ).order_by(Email.date_sent.desc()).limit(100).all()
        
        return render_template('search.html', results=results, query=query)
