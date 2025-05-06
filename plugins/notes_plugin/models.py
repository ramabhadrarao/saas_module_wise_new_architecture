"""Note data models"""
from flask_sqlalchemy import SQLAlchemy
from app import db
from app.core.db import BaseModel
from datetime import datetime

class Note(BaseModel):
    """Note model for storing user notes"""
    __tablename__ = 'notes_plugin_notes'
    
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), nullable=True)
    
    # Foreign keys
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    tenant = db.relationship('Tenant', backref=db.backref('notes', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('notes', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Note {self.title}>'
    
    @classmethod
    def create_note(cls, tenant_id, user_id, title, content, category=None):
        """Create a new note"""
        note = cls(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            content=content,
            category=category
        )
        db.session.add(note)
        db.session.commit()
        return note
    
    @classmethod
    def get_notes_for_user(cls, user_id, include_archived=False):
        """Get all notes for a user"""
        query = cls.query.filter_by(user_id=user_id)
        
        if not include_archived:
            query = query.filter_by(is_archived=False)
            
        return query.order_by(cls.is_pinned.desc(), cls.updated_at.desc()).all()
    
    @classmethod
    def get_notes_by_category(cls, user_id, category, include_archived=False):
        """Get notes for a user filtered by category"""
        query = cls.query.filter_by(user_id=user_id, category=category)
        
        if not include_archived:
            query = query.filter_by(is_archived=False)
            
        return query.order_by(cls.is_pinned.desc(), cls.updated_at.desc()).all()