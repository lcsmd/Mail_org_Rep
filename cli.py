#!/usr/bin/env python3
"""
Command-line interface for AI-Enhanced Email Management System.
"""

import argparse
import os
import sys

from app import app, db
from email_processor import process_new_emails
from models import EmailAccount, Category


def setup_database():
    """Initialize the database."""
    with app.app_context():
        db.create_all()
        print("Database initialized.")


def list_accounts():
    """List all configured email accounts."""
    with app.app_context():
        accounts = EmailAccount.query.all()
        if not accounts:
            print("No email accounts configured.")
            return
        
        print(f"Found {len(accounts)} email account(s):")
        for account in accounts:
            print(f"  - {account.email} ({account.account_type})")


def list_categories():
    """List all email categories."""
    with app.app_context():
        categories = Category.query.all()
        if not categories:
            print("No categories configured.")
            return
        
        print(f"Found {len(categories)} categories:")
        for category in categories:
            parent = category.parent.name if category.parent else "None"
            print(f"  - {category.name} (Parent: {parent})")


def sync_emails():
    """Synchronize emails from all configured accounts."""
    print("Syncing emails from all accounts...")
    with app.app_context():
        result = process_new_emails()
        print(f"Processed {result.get('processed_count', 0)} emails.")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="AI-Enhanced Email Management System CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Initialize the database")
    
    # List accounts command
    list_accounts_parser = subparsers.add_parser("list-accounts", help="List configured email accounts")
    
    # List categories command
    list_categories_parser = subparsers.add_parser("list-categories", help="List email categories")
    
    # Sync emails command
    sync_parser = subparsers.add_parser("sync", help="Synchronize emails from all accounts")
    
    # Run web app command
    run_parser = subparsers.add_parser("run", help="Run the web application")
    run_parser.add_argument("--host", default="0.0.0.0", help="Host to run the server on")
    run_parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    run_parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup_database()
    elif args.command == "list-accounts":
        list_accounts()
    elif args.command == "list-categories":
        list_categories()
    elif args.command == "sync":
        sync_emails()
    elif args.command == "run":
        print(f"Starting web server on {args.host}:{args.port}...")
        app.run(host=args.host, port=args.port, debug=args.debug)
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())