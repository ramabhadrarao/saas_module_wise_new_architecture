"""Role-based access control implementation"""
from functools import wraps
from flask import abort, g, current_app
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

def permission_required(permission):
    """Decorator for checking if current user has a specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not current_user.has_permission(permission):
                logger.warning(f"User {current_user.username} attempted to access a resource requiring {permission} permission")
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_required(role_name):
    """Decorator for checking if current user has a specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not current_user.has_role(role_name):
                logger.warning(f"User {current_user.username} attempted to access a resource requiring {role_name} role")
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def tenant_admin_required(f):
    """Decorator for checking if current user is a tenant admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        
        if not current_user.is_tenant_admin and not current_user.is_system_admin:
            logger.warning(f"User {current_user.username} attempted to access a tenant admin resource")
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def system_admin_required(f):
    """Decorator for checking if current user is a system admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        
        if not current_user.is_system_admin:
            logger.warning(f"User {current_user.username} attempted to access a system admin resource")
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def same_tenant_required(f):
    """Decorator for checking if the resource belongs to the same tenant as the user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        
        # System admins can access any tenant's resources
        if current_user.is_system_admin:
            return f(*args, **kwargs)
        
        # Check if tenant ID in URL matches user's tenant
        tenant_id = kwargs.get('tenant_id')
        if tenant_id and int(tenant_id) != current_user.tenant_id:
            logger.warning(f"User {current_user.username} attempted to access a resource from another tenant")
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function