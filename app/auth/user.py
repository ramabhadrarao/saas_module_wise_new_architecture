"""User model and authentication logic"""
from flask import current_app
from flask_login import UserMixin,AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.core.db import BaseModel
from app.tenant.tenant import Tenant
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta
import uuid
import jwt
import logging

logger = logging.getLogger(__name__)

# Association table for user-role relationship
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

class User(UserMixin, BaseModel):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    # User identification
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))

    
    # User profile
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    is_active = db.Column(db.Boolean, default=True)
    
    # User metadata
    last_login = db.Column(db.DateTime)
    user_settings = db.Column(JSONB, default={})
    
    # Multi-tenancy
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))
    is_tenant_admin = db.Column(db.Boolean, default=False)
    is_system_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    tenant = db.relationship('Tenant', backref=db.backref('users', lazy='dynamic'))
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                           backref=db.backref('users', lazy=True))
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def password(self):
        """Prevent password from being accessed"""
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        """Check if password matches"""
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def has_permission(self, permission):
        """Check if user has a specific permission"""
        # System admins have all permissions
        if self.is_system_admin:
            return True
        
        # Check if any of the user's roles have the permission
        for role in self.roles:
            if permission in role.permissions:
                return True
        
        return False
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)
    
    def generate_auth_token(self, expiration=3600):
        """Generate authentication token"""
        payload = {
            'user_id': self.id,
            'exp': datetime.utcnow() + timedelta(seconds=expiration),
            'iat': datetime.utcnow()
        }
        return jwt.encode(
            payload,
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
    
    @staticmethod
    def verify_auth_token(token):
        """Verify authentication token and return user"""
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            return User.query.get(payload['user_id'])
        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Invalid token
            return None
    
    @staticmethod
    def create_user(email, username, password, tenant_id=None, 
                   first_name=None, last_name=None, is_tenant_admin=False, 
                   is_system_admin=False):
        """Create a new user"""
        user = User(
            email=email,
            username=username,
            tenant_id=tenant_id,
            first_name=first_name,
            last_name=last_name,
            is_tenant_admin=is_tenant_admin,
            is_system_admin=is_system_admin
        )
        user.password = password
        
        try:
            db.session.add(user)
            db.session.commit()
            logger.info(f"User created: {username}")
            return user
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()

class Role(BaseModel):
    """Role model for role-based access control"""
    __tablename__ = 'roles'
    
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(JSONB, default=[])
    
    # Multi-tenancy
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))
    is_system_role = db.Column(db.Boolean, default=False)
    
    # Relationships
    tenant = db.relationship('Tenant', backref=db.backref('roles', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def has_permission(self, permission):
        """Check if role has a specific permission"""
        return permission in self.permissions
    
    def add_permission(self, permission):
        """Add a permission to the role"""
        if not self.has_permission(permission):
            self.permissions.append(permission)
            db.session.commit()
            logger.info(f"Permission {permission} added to role {self.name}")
    
    def remove_permission(self, permission):
        """Remove a permission from the role"""
        if self.has_permission(permission):
            self.permissions.remove(permission)
            db.session.commit()
            logger.info(f"Permission {permission} removed from role {self.name}")
    
    @staticmethod
    def insert_default_roles():
        """Insert default roles"""
        default_roles = {
            'Admin': {
                'description': 'Administrator with full access',
                'permissions': [
                    'admin_access', 'system_config',
                    'view_tenant', 'create_tenant', 'edit_tenant', 'delete_tenant',
                    'view_users', 'create_user', 'edit_user', 'delete_user',
                    'view_roles', 'create_role', 'edit_role', 'delete_role',
                    'view_plugins', 'install_plugin', 'uninstall_plugin', 'configure_plugin'
                ],
                'is_system_role': True
            },
            'Tenant Admin': {
                'description': 'Tenant administrator with full access to tenant resources',
                'permissions': [
                    'view_tenant', 'edit_tenant',
                    'view_users', 'create_user', 'edit_user', 'delete_user',
                    'view_roles', 'create_role', 'edit_role', 'delete_role',
                    'view_plugins', 'configure_plugin'
                ],
                'is_system_role': True
            },
            'User': {
                'description': 'Regular user with basic access',
                'permissions': [
                    'view_tenant',
                    'view_users'
                ],
                'is_system_role': True
            }
        }
        
        for role_name, role_data in default_roles.items():
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(
                    name=role_name,
                    description=role_data['description'],
                    permissions=role_data['permissions'],
                    is_system_role=role_data['is_system_role']
                )
                db.session.add(role)
                logger.info(f"Default role created: {role_name}")
        
        db.session.commit()

class AnonymousUser(AnonymousUserMixin):
    """Anonymous user class with default permission methods"""
    
    def has_permission(self, permission):
        """Anonymous users have no permissions"""
        return False
    
    def has_role(self, role_name):
        """Anonymous users have no roles"""
        return False
    
    @property
    def is_tenant_admin(self):
        """Anonymous users are not tenant admins"""
        return False
    
    @property
    def is_system_admin(self):
        """Anonymous users are not system admins"""
        return False