from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import current_user, login_required
from app.tenant.tenant import Tenant
from app.auth.user import User
from datetime import datetime
from sqlalchemy import func
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """Main application dashboard - role-based content"""
    # Different dashboard view based on role
    if current_user.is_system_admin:
        # System admin dashboard with all tenants
        tenants = Tenant.query.all()
        user_count = User.query.count()
        active_user_count = User.query.filter_by(is_active=True).count()
        tenant_count = Tenant.query.count()
        active_tenant_count = Tenant.query.filter_by(status='active').count()
        
        # Get user counts for each tenant
        tenant_user_counts = {}
        tenant_users = User.query.with_entities(User.tenant_id, func.count(User.id)) \
                          .group_by(User.tenant_id).all()
        for tenant_id, count in tenant_users:
            if tenant_id:  # Skip None tenant_id
                tenant_user_counts[tenant_id] = count
        
        # Get plugin stats
        plugins = []
        active_plugins = []
        tenant_plugins = []
        
        # Only fetch plugin data if plugin module is available
        try:
            from app.plugins.plugin import Plugin
            from app.plugins.tenant_plugin import TenantPlugin
            
            plugins = Plugin.query.all()
            active_plugins = Plugin.query.filter_by(status='active').all()
            tenant_plugins = TenantPlugin.query.filter_by(enabled=True).all()
        except ImportError:
            # Plugin module not available yet
            pass
        
        return render_template('dashboard/admin_dashboard.html', 
                              title='System Dashboard',
                              tenants=tenants,
                              user_count=user_count,
                              active_user_count=active_user_count,
                              tenant_count=tenant_count,
                              active_tenant_count=active_tenant_count,
                              tenant_user_counts=tenant_user_counts,
                              plugins=plugins,
                              active_plugins=active_plugins,
                              tenant_plugins=tenant_plugins)
    
    elif current_user.is_tenant_admin:
        # Tenant admin dashboard
        tenant = current_user.tenant
        tenant_users = User.query.filter_by(tenant_id=tenant.id).all() if tenant else []
        
        # Get tenant plugins if plugin module is available
        tenant_plugins = []
        try:
            if tenant:
                from app.plugins.tenant_plugin import TenantPlugin
                from app.plugins.plugin import Plugin
                
                # Get enabled plugins for this tenant
                tenant_plugin_records = TenantPlugin.query.filter_by(
                    tenant_id=tenant.id,
                    enabled=True
                ).join(Plugin).filter(
                    Plugin.status == 'active'
                ).all()
                
                tenant_plugins = [tp.plugin for tp in tenant_plugin_records]
        except ImportError:
            # Plugin module not available yet
            pass
        
        return render_template('dashboard/tenant_admin_dashboard.html',
                              title='Tenant Admin Dashboard',
                              tenant=tenant,
                              users=tenant_users,
                              tenant_plugins=tenant_plugins)
    
    else:
        # Regular user dashboard
        # Get user's tenant plugins if plugin module is available
        tenant_plugins = []
        try:
            tenant = current_user.tenant
            if tenant:
                from app.plugins.tenant_plugin import TenantPlugin
                from app.plugins.plugin import Plugin
                
                # Get enabled plugins for this tenant
                tenant_plugin_records = TenantPlugin.query.filter_by(
                    tenant_id=tenant.id,
                    enabled=True
                ).join(Plugin).filter(
                    Plugin.status == 'active'
                ).all()
                
                tenant_plugins = [tp.plugin for tp in tenant_plugin_records]
        except ImportError:
            # Plugin module not available yet
            pass
            
        return render_template('dashboard/user_dashboard.html',
                             title='Dashboard',
                             tenant_plugins=tenant_plugins)

@main_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'ok', 'message': 'Service is running'}