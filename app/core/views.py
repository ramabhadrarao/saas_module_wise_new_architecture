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
        
        return render_template('dashboard/admin_dashboard.html', 
                              title='System Dashboard',
                              tenants=tenants,
                              user_count=user_count,
                              active_user_count=active_user_count,
                              tenant_count=tenant_count,
                              active_tenant_count=active_tenant_count,
                              tenant_user_counts=tenant_user_counts)
    
    elif current_user.is_tenant_admin:
        # Tenant admin dashboard
        tenant = current_user.tenant
        tenant_users = User.query.filter_by(tenant_id=tenant.id).all() if tenant else []
        
        return render_template('dashboard/tenant_admin_dashboard.html',
                              title='Tenant Admin Dashboard',
                              tenant=tenant,
                              users=tenant_users)
    
    else:
        # Regular user dashboard
        return render_template('dashboard/user_dashboard.html',
                             title='Dashboard')

@main_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'ok', 'message': 'Service is running'}