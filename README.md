# AI-Enhanced Email Management System

An intelligent email management system that processes, categorizes, and organizes emails from multiple sources with OAuth integration and advanced AI-powered analysis.

## Key Features

- **Multi-platform Email Integration**: Connect to Gmail and Microsoft Exchange accounts
- **OAuth Authentication**: Secure authentication with multiple email providers
- **Intelligent Email Processing**: AI-powered analysis and categorization
- **Dynamic Organization**: Smart categorization and rule-based filtering
- **Enhanced Error Handling**: User-friendly error reporting
- **Voice Interface**: AI assistant interaction (coming soon)
- **Timeline View**: Visualize email threads (coming soon)
- **Knowledge Base**: Extract and organize information (coming soon)

## Technical Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **Authentication**: OAuth 2.0
- **AI**: OpenAI API (GPT-4o)
- **Email APIs**: Gmail API, Microsoft Graph API

## Project Structure

- `app.py`: Main Flask application
- `models.py`: SQLAlchemy database models
- `email_processor.py`: Email processing logic
- `email_services.py`: Email provider integrations
- `ai_service.py`: OpenAI integration for email analysis
- `storage.py`: File storage management
- `templates/`: HTML templates
- `static/`: CSS, JavaScript, and assets

## Setup Instructions

1. Clone this repository
2. Install dependencies with `pip install -r requirements.txt`
3. Configure environment variables:
   - `DATABASE_URL`: PostgreSQL connection string
   - `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`: Google API credentials
   - `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_TENANT_ID`: Microsoft API credentials
   - `OPENAI_API_KEY`: OpenAI API key
4. Initialize the database with `flask db upgrade`
5. Run the application with `gunicorn --bind 0.0.0.0:5000 main:app`

## OAuth Configuration

### Google OAuth

1. Create credentials at https://console.cloud.google.com/apis/credentials
2. Configure redirect URI as `https://<your-domain>/accounts/add/gmail`
3. Enable Gmail API

### Microsoft OAuth

1. Register application at https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
2. Add redirect URI as `https://<your-domain>/accounts/add/exchange`
3. Configure API permissions for `mail.read`

## License

This project is licensed under the MIT License - see the LICENSE file for details.