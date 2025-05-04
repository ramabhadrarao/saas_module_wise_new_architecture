from flask import request, g, current_app
from werkzeug.local import LocalProxy
from functools import wraps
from app.tenant.tenant import Tenant
import logging

logger = logging.getLogger(__name__)

def get_current_tenant():
    """Get the current tenant from Flask g object"""
    if 'tenant' not in g:
        g.tenant = identify_tenant()
    return g.tenant

# Create a proxy for the current tenant
current_tenant = LocalProxy(get_current_tenant)

def identify_tenant():
    """
    Identify the current tenant based on request information.
    Returns None if no tenant is identified.
    """
    # Check for tenant slug in subdomain (e.g., tenant-slug.example.com)
    host = request.host.split(':')[0]  # Remove port if present
    parts = host.split('.')
    
    # Skip identification for certain paths (like static files)
    if request.path.startswith('/static/'):
        return None
    
    # Check if we have a subdomain and it's not 'www'
    if len(parts) > 2 and parts[0] != 'www':
        # Try to get tenant by subdomain
        tenant = Tenant.get_tenant_by_slug(parts[0])
        if tenant:
            logger.debug(f"Tenant identified by subdomain: {tenant.name}")
            return tenant
    
    # Check for custom domain mapping
    tenant = Tenant.get_tenant_by_domain(host)
    if tenant:
        logger.debug(f"Tenant identified by domain: {tenant.name}")
        return tenant
    
    # Check for tenant slug in URL path (e.g., /tenant/{slug}/)
    path_parts = request.path.split('/')
    if len(path_parts) > 2 and path_parts[1] == 'tenant':
        tenant_slug = path_parts[2]
        tenant = Tenant.get_tenant_by_slug(tenant_slug)
        if tenant:
            logger.debug(f"Tenant identified by URL path: {tenant.name}")
            return tenant
    
    # Check for tenant in query string (e.g., ?tenant=slug)
    tenant_slug = request.args.get('tenant')
    if tenant_slug:
        tenant = Tenant.get_tenant_by_slug(tenant_slug)
        if tenant:
            logger.debug(f"Tenant identified by query parameter: {tenant.name}")
            return tenant
    
    # No tenant identified
    return None

def tenant_required(f):
    """Decorator to require a tenant for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant = get_current_tenant()
        if tenant is None:
            # Redirect to tenant selection page or show error
            return current_app.login_manager.unauthorized()
        return f(*args, **kwargs)
    return decorated_function

def set_tenant_schema_for_connection(connection, tenant):
    """Set the search path for the connection to the tenant's schema"""
    if tenant:
        connection.execute(f'SET search_path TO "{tenant.schema_name}", public')
    else:
        connection.execute('SET search_path TO public')

def tenant_middleware(app):
    """Middleware to identify tenant and set up request context"""
    
    @app.before_request
    def identify_tenant_before_request():
        """Identify the tenant from the request and store in Flask g"""
        tenant = identify_tenant()
        g.tenant = tenant
        
        if tenant:
            # Set PostgreSQL schema search path to the tenant's schema
            # This would be added when we have user authentication
            # and when we have tenant-specific database models
            pass
    
    @app.teardown_request
    def reset_tenant_after_request(exception=None):
        """Clear tenant from request context"""
        if hasattr(g, 'tenant'):
            del g.tenant