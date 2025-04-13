"""
Setup script for AI-Enhanced Email Management System.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="emailmanagement",
    version="0.1.0",
    author="lcsmd",
    author_email="l@lcs.nyc",
    description="AI-Enhanced Email Management System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lcsmd/Mail_org_Rep",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "beautifulsoup4>=4.12.2",
        "email-validator>=2.1.0",
        "flask>=3.0.0",
        "flask-login>=0.6.3",
        "flask-sqlalchemy>=3.1.1",
        "gunicorn>=23.0.0",
        "oauthlib>=3.2.2",
        "openai>=1.10.0",
        "psycopg2-binary>=2.9.9",
        "requests>=2.31.0",
        "sqlalchemy>=2.0.23",
        "werkzeug>=3.0.1",
    ],
)