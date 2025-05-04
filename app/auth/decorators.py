"""Route protection utilities"""
from functools import wraps
from flask import abort, redirect, url_for, flash, request, g
from flask_login import current_user
from app.tenant.tenant import Tenant
from app.tenant.middleware import get_current_tenant
import logging

logger = logging.getLogger(__name__)

def login_required(f):
    """Decorator for requiring login to access a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def active_required(f):
    """Decorator for requiring an active user account"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if not current_user.is_active:
            flash('Your account is inactive. Please contact support.', 'warning')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def tenant_required(f):
    """Decorator to require a tenant context for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant = get_current_tenant()
        if tenant is None:
            flash('No tenant context found', 'warning')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def tenant_active_required(f):
    """Decorator to require an active tenant for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant = get_current_tenant()
        if tenant is None:
            flash('No tenant context found', 'warning')
            return redirect(url_for('main.index'))
        
        if tenant.status != 'active':
            flash(f'Tenant {tenant.name} is currently {tenant.status}', 'warning')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def check_permission(permission):
    """Check if current user has a specific permission"""
    if not current_user.is_authenticated:
        return False
    
    return current_user.has_permission(permission)

def can_access_tenant(tenant_id):
    """Check if current user can access a specific tenant"""
    if not current_user.is_authenticated:
        return False
    
    # System admins can access any tenant
    if current_user.is_system_admin:
        return True
    
    # Users can only access their own tenant
    return current_user.tenant_id == tenant_id