# Contributing to AI-Enhanced Email Management System

Thank you for considering contributing to this project! Here's how you can help.

## Development Setup

1. Fork the repository and clone it locally.
2. Install dependencies:
   ```
   pip install -e .
   ```
3. Configure environment variables:
   ```
   export DATABASE_URL="postgresql://username:password@localhost/email_manager"
   export GOOGLE_OAUTH_CLIENT_ID="your_google_client_id"
   export GOOGLE_OAUTH_CLIENT_SECRET="your_google_client_secret"
   export MS_CLIENT_ID="your_microsoft_client_id"
   export MS_CLIENT_SECRET="your_microsoft_client_secret"
   export MS_TENANT_ID="your_microsoft_tenant_id"
   export OPENAI_API_KEY="your_openai_api_key"
   ```
4. Initialize the database:
   ```
   python cli.py setup
   ```
5. Run the application:
   ```
   python cli.py run --debug
   ```

## Pull Request Process

1. Update the README.md with details of changes if needed.
2. Update the documentation with any new features or API changes.
3. The PR should work with Python 3.8 or higher.
4. Ensure that any new code follows the existing style.

## Code Style

This project follows PEP 8 style guidelines. Please ensure your code complies with these standards.

## Testing

Before submitting a PR, please test your changes thoroughly. The project uses Flask's built-in test client for testing.

## Future Development

Here are some areas where contributions would be especially valuable:

- Voice interface implementation
- Timeline view for email threads
- Knowledge base creation from extracted information
- Enhanced email categorization with machine learning
- Improved OAuth integration with additional providers

Thank you for your interest in improving this project!