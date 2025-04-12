from app import db
from sqlalchemy import Table, Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

# Many-to-many relationships
email_attachments = Table('email_attachments', db.Model.metadata,
    Column('email_id', String, ForeignKey('email.id')),
    Column('attachment_id', String, ForeignKey('attachment.id'))
)

email_html_objects = Table('email_html_objects', db.Model.metadata,
    Column('email_id', String, ForeignKey('email.id')),
    Column('html_object_id', String, ForeignKey('html_object.id'))
)

email_disclaimers = Table('email_disclaimers', db.Model.metadata,
    Column('email_id', String, ForeignKey('email.id')),
    Column('disclaimer_id', String, ForeignKey('disclaimer.id'))
)

email_categories = Table('email_categories', db.Model.metadata,
    Column('email_id', String, ForeignKey('email.id')),
    Column('category_id', Integer, ForeignKey('category.id'))
)

email_rules = Table('email_rules', db.Model.metadata,
    Column('email_id', String, ForeignKey('email.id')),
    Column('rule_id', Integer, ForeignKey('rule.id'))
)

thread_emails = Table('thread_emails', db.Model.metadata,
    Column('thread_id', String, ForeignKey('thread.id')),
    Column('email_id', String, ForeignKey('email.id'))
)

thread_categories = Table('thread_categories', db.Model.metadata,
    Column('thread_id', String, ForeignKey('thread.id')),
    Column('category_id', Integer, ForeignKey('category.id'))
)

thread_rules = Table('thread_rules', db.Model.metadata,
    Column('thread_id', String, ForeignKey('thread.id')),
    Column('rule_id', Integer, ForeignKey('rule.id'))
)

contact_categories = Table('contact_categories', db.Model.metadata,
    Column('contact_id', Integer, ForeignKey('contact.id')),
    Column('category_id', Integer, ForeignKey('category.id'))
)

group_contacts = Table('group_contacts', db.Model.metadata,
    Column('group_id', Integer, ForeignKey('group.id')),
    Column('contact_id', Integer, ForeignKey('contact.id'))
)

group_categories = Table('group_categories', db.Model.metadata,
    Column('group_id', Integer, ForeignKey('group.id')),
    Column('category_id', Integer, ForeignKey('category.id'))
)

group_threads = Table('group_threads', db.Model.metadata,
    Column('group_id', Integer, ForeignKey('group.id')),
    Column('thread_id', String, ForeignKey('thread.id'))
)

domain_categories = Table('domain_categories', db.Model.metadata,
    Column('domain_id', Integer, ForeignKey('domain.id')),
    Column('category_id', Integer, ForeignKey('category.id'))
)

domain_rules = Table('domain_rules', db.Model.metadata,
    Column('domain_id', Integer, ForeignKey('domain.id')),
    Column('rule_id', Integer, ForeignKey('rule.id'))
)

# Email account model
class EmailAccount(db.Model):
    __tablename__ = 'email_account'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(128), unique=True, nullable=False)
    account_type = Column(String(20), nullable=False)  # 'gmail' or 'exchange'
    display_name = Column(String(128))
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expiry = Column(DateTime)
    last_sync = Column(DateTime)
    
    def __repr__(self):
        return f'<EmailAccount {self.email}>'

# Email model
class Email(db.Model):
    __tablename__ = 'email'
    
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(Integer, ForeignKey('email_account.id'))
    message_id = Column(String(256))  # Original email Message-ID header
    sender = Column(String(256))  # From field
    recipients = Column(Text)  # To field, JSON serialized list
    cc = Column(Text)  # CC field, JSON serialized list
    bcc = Column(Text)  # BCC field, JSON serialized list
    subject = Column(Text)
    date_sent = Column(DateTime, index=True)
    format = Column(String(10))  # 'text' or 'html'
    body_id = Column(String(64), ForeignKey('body.id'))
    thread_id = Column(String(64), ForeignKey('thread.id'), index=True)
    priority = Column(Integer, default=0)
    spam_score = Column(Float, default=0.0)
    is_read = Column(Boolean, default=False)
    is_confidential = Column(Boolean, default=False)
    retention_policy = Column(String(64))
    forwarded_from = Column(String(64), ForeignKey('email.id'))
    
    # Relationships
    account = relationship('EmailAccount', backref='emails')
    body = relationship('Body', backref='emails')
    thread = relationship('Thread', backref='emails')
    attachments = relationship('Attachment', secondary=email_attachments, backref='emails')
    html_objects = relationship('HTMLObject', secondary=email_html_objects, backref='emails')
    disclaimers = relationship('Disclaimer', secondary=email_disclaimers, backref='emails')
    categories = relationship('Category', secondary=email_categories, backref='emails')
    rules = relationship('Rule', secondary=email_rules, backref='emails')
    forwarded_emails = relationship('Email', backref=db.backref('forwarded_from_email', remote_side=[id]))
    
    def __repr__(self):
        return f'<Email {self.id}: {self.subject}>'

# Body model
class Body(db.Model):
    __tablename__ = 'body'
    
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(String(256))  # Path to the body file (.bod or .hbod)
    
    # Relationships
    disclaimers = relationship('Disclaimer', secondary='body_disclaimers')
    
    def __repr__(self):
        return f'<Body {self.id}>'

# Many-to-many relationship for body and disclaimers
body_disclaimers = Table('body_disclaimers', db.Model.metadata,
    Column('body_id', String, ForeignKey('body.id')),
    Column('disclaimer_id', String, ForeignKey('disclaimer.id'))
)

# Attachment model
class Attachment(db.Model):
    __tablename__ = 'attachment'
    
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(String(256))  # Path to the attachment file
    filename = Column(String(256))  # Original filename
    content_type = Column(String(128))  # MIME type
    size = Column(Integer)  # Size in bytes
    
    def __repr__(self):
        return f'<Attachment {self.id}: {self.filename}>'

# HTML Object model
class HTMLObject(db.Model):
    __tablename__ = 'html_object'
    
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(String(256))  # Path to the HTML object file
    content_type = Column(String(128))  # MIME type
    
    def __repr__(self):
        return f'<HTMLObject {self.id}>'

# Disclaimer model
class Disclaimer(db.Model):
    __tablename__ = 'disclaimer'
    
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    text = Column(Text)
    
    def __repr__(self):
        return f'<Disclaimer {self.id}>'

# Thread model
class Thread(db.Model):
    __tablename__ = 'thread'
    
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    date_started = Column(DateTime)
    last_date = Column(DateTime)
    subject = Column(Text)
    priority = Column(Integer, default=0)
    
    # Relationships
    categories = relationship('Category', secondary=thread_categories, backref='threads')
    rules = relationship('Rule', secondary=thread_rules, backref='threads')
    
    def __repr__(self):
        return f'<Thread {self.id}>'

# Contact model
class Contact(db.Model):
    __tablename__ = 'contact'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(256), unique=True, nullable=False)
    firstname = Column(String(128))
    lastname = Column(String(128))
    priority = Column(Integer, default=0)
    retention_policy = Column(String(64))
    sent_count = Column(Integer, default=0)
    received_count = Column(Integer, default=0)
    
    # Relationships
    categories = relationship('Category', secondary=contact_categories, backref='contacts')
    
    def __repr__(self):
        return f'<Contact {self.email}>'

# Group model
class Group(db.Model):
    __tablename__ = 'group'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)
    priority = Column(Integer, default=0)
    retention_policy = Column(String(64))
    sent_count = Column(Integer, default=0)
    
    # Relationships
    contacts = relationship('Contact', secondary=group_contacts, backref='groups')
    categories = relationship('Category', secondary=group_categories, backref='groups')
    threads = relationship('Thread', secondary=group_threads, backref='groups')
    
    def __repr__(self):
        return f'<Group {self.name}>'

# Domain model
class Domain(db.Model):
    __tablename__ = 'domain'
    
    id = Column(Integer, primary_key=True)
    email_domain = Column(String(128), unique=True, nullable=False)
    priority = Column(Integer, default=0)
    retention_policy = Column(String(64))
    sent_count = Column(Integer, default=0)
    received_count = Column(Integer, default=0)
    
    # Relationships
    categories = relationship('Category', secondary=domain_categories, backref='domains')
    rules = relationship('Rule', secondary=domain_rules, backref='domains')
    
    def __repr__(self):
        return f'<Domain {self.email_domain}>'

# Rule model
class Rule(db.Model):
    __tablename__ = 'rule'
    
    id = Column(Integer, primary_key=True)
    type = Column(String(128), nullable=False)  # AI-assigned (a:), User-assigned (u:), Rule-based (r:)
    targets = Column(Text)  # JSON serialized targets
    parameters = Column(Text)  # JSON serialized parameters
    results = Column(Text)  # JSON serialized results
    applied_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Rule {self.id}: {self.type}>'

# Category model
class Category(db.Model):
    __tablename__ = 'category'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey('category.id'))
    assigned_count = Column(Integer, default=0)
    
    # Self-referential relationship for parent-child categories
    subcategories = relationship('Category', backref=db.backref('parent', remote_side=[id]))
    
    def __repr__(self):
        return f'<Category {self.name}>'

# Keyword model
class Keyword(db.Model):
    __tablename__ = 'keyword'
    
    id = Column(Integer, primary_key=True)
    text = Column(String(128), unique=True, nullable=False)
    assigned_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f'<Keyword {self.text}>'

# Many-to-many relationship for keywords and emails
keyword_emails = Table('keyword_emails', db.Model.metadata,
    Column('keyword_id', Integer, ForeignKey('keyword.id')),
    Column('email_id', String, ForeignKey('email.id'))
)
