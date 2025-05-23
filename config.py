import os

# Application configuration
class Config:
    """Base configuration class."""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SESSION_SECRET", "development-secret-key")
    
    # Database
    SQLALCHEMY_DATABASE_URI = "sqlite:///email_manager.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Use the development domain provided by Replit
    replit_dev_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    replit_domain = f"https://{replit_dev_domain}" if replit_dev_domain else f"https://{os.environ.get('REPL_SLUG')}.{os.environ.get('REPL_OWNER')}.repl.co"
    
    # API keys and credentials - explicitly setting as instance variables 
    # so they'll be accessible in templates
    GMAIL_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or os.environ.get("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or os.environ.get("GMAIL_CLIENT_SECRET", "")
    MS_CLIENT_ID = os.environ.get("MS_CLIENT_ID", "")
    MS_CLIENT_SECRET = os.environ.get("MS_CLIENT_SECRET", "")
    
    # OAuth redirect URIs
    GMAIL_REDIRECT_URI = os.environ.get("GMAIL_REDIRECT_URI", f"{replit_domain}/accounts/add/gmail")
    MS_REDIRECT_URI = os.environ.get("MS_REDIRECT_URI", f"{replit_domain}/accounts/add/exchange")
    
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    
    # Storage
    STORAGE_DIR = os.environ.get("STORAGE_DIR", "./email_storage")
    
    # Email processing
    MAX_EMAILS_PER_FETCH = 50
    
    # AI settings
    AI_MODEL = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

class ProductionConfig(Config):
    """Production configuration."""
    # In production, make sure SESSION_SECRET is set in environment variables
    
    # Use a more robust database in production
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///email_manager.db")

# Get the current configuration
config_name = os.environ.get("FLASK_ENV", "development")
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig
}
current_config = config_map.get(config_name, DevelopmentConfig)
