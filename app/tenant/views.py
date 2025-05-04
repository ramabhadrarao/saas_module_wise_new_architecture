from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app import db
from app.tenant.tenant import Tenant, TenantStatus
from app.tenant.quota import QuotaManager, ResourceType
import logging
from datetime import datetime
logger = logging.getLogger(__name__)

# Create blueprint
tenant_bp = Blueprint('tenant', __name__, url_prefix='/tenant')

@tenant_bp.route('/')
def index():
    """Tenant management dashboard"""
    # TODO: Add authorization check for admin
    
    # Get all tenants
    tenants = Tenant.query.all()
    
    # Get usage data for each tenant
    tenant_data = []
    for tenant in tenants:
        user_usage = QuotaManager.get_usage(tenant, ResourceType.USERS)
        storage_usage = QuotaManager.get_usage(tenant, ResourceType.STORAGE)
        
        tenant_data.append({
            'id': tenant.id,
            'name': tenant.name,
            'slug': tenant.slug,
            'domain': tenant.domain,
            'status': tenant.status,
            'plan': tenant.plan,
            'owner_email': tenant.owner_email,
            'quotas': {  # Add this explicitly
                'max_users': tenant.max_users,
                'max_storage_mb': tenant.max_storage_mb
            },
            'usage': {
                'users': user_usage,
                'storage_mb': storage_usage,
                'users_percentage': QuotaManager.get_usage_percentage(tenant, ResourceType.USERS),
                'storage_percentage': QuotaManager.get_usage_percentage(tenant, ResourceType.STORAGE)
            }
        })
    
    return render_template('tenant/dashboard.html', 
                          title='Tenant Management', 
                          tenants=tenant_data)

@tenant_bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new tenant"""
    # TODO: Add authorization check for admin
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        owner_email = request.form.get('owner_email')
        description = request.form.get('description')
        domain = request.form.get('domain')
        plan = request.form.get('plan', 'free')
        
        # Validate required fields
        if not name or not owner_email:
            flash('Name and owner email are required', 'danger')
            return render_template('tenant/create.html', title='Create Tenant')
        
        try:
            # Print debugging information
            print(f"Creating tenant: {name}, {owner_email}, {domain}, {plan}")
            
            # Create the tenant
            tenant = Tenant.create_tenant(
                name=name,
                owner_email=owner_email,
                description=description,
                domain=domain,
                plan=plan
            )
            
            flash(f"Tenant '{tenant.name}' created successfully", 'success')
            return redirect(url_for('tenant.view', slug=tenant.slug))
            
        except Exception as e:
            # Log the full exception
            import traceback
            print(f"Error creating tenant: {str(e)}")
            print(traceback.format_exc())
            
            flash(f"Failed to create tenant: {str(e)}", 'danger')
    
    return render_template('tenant/create.html', title='Create Tenant')

@tenant_bp.route('/<slug>', methods=['GET'])
def view(slug):
    """View tenant details"""
    # TODO: Add authorization check for admin or tenant owner
    
    tenant = Tenant.get_tenant_by_slug(slug)
    if not tenant:
        flash(f"Tenant '{slug}' not found", 'warning')
        return redirect(url_for('tenant.index'))
    
    # Get usage data
    user_usage = QuotaManager.get_usage(tenant, ResourceType.USERS)
    storage_usage = QuotaManager.get_usage(tenant, ResourceType.STORAGE)
    
    tenant_data = {
        'id': tenant.id,
        'name': tenant.name,
        'slug': tenant.slug,
        'schema_name': tenant.schema_name,
        'domain': tenant.domain,
        'description': tenant.description,
        'status': tenant.status,
        'plan': tenant.plan,
        'owner_email': tenant.owner_email,
        'created_at': tenant.created_at,
        'updated_at': tenant.updated_at,
        'quotas': {
            'max_users': tenant.max_users,
            'max_storage_mb': tenant.max_storage_mb
        },
        'usage': {
            'users': user_usage,
            'storage_mb': storage_usage,
            'users_percentage': QuotaManager.get_usage_percentage(tenant, ResourceType.USERS),
            'storage_percentage': QuotaManager.get_usage_percentage(tenant, ResourceType.STORAGE)
        }
    }
    
    return render_template('tenant/settings.html', 
                          title=f"Tenant: {tenant.name}", 
                          tenant=tenant_data,
                          now=datetime.now())

@tenant_bp.route('/<slug>/edit', methods=['GET', 'POST'])
def edit(slug):
    """Edit tenant details"""
    # TODO: Add authorization check for admin or tenant owner
    
    tenant = Tenant.get_tenant_by_slug(slug)
    if not tenant:
        flash(f"Tenant '{slug}' not found", 'warning')
        return redirect(url_for('tenant.index'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        domain = request.form.get('domain')
        plan = request.form.get('plan')
        max_users = request.form.get('max_users')
        max_storage_mb = request.form.get('max_storage_mb')
        
        # Validate required fields
        if not name:
            flash('Name is required', 'danger')
            return redirect(url_for('tenant.edit', slug=slug))
        
        try:
            # Update tenant
            tenant.name = name
            tenant.description = description
            tenant.domain = domain
            tenant.plan = plan
            
            if max_users and max_users.isdigit():
                tenant.max_users = int(max_users)
                
            if max_storage_mb and max_storage_mb.isdigit():
                tenant.max_storage_mb = int(max_storage_mb)
            
            db.session.commit()
            
            flash(f"Tenant '{tenant.name}' updated successfully", 'success')
            return redirect(url_for('tenant.view', slug=tenant.slug))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating tenant: {str(e)}")
            flash(f"Failed to update tenant: {str(e)}", 'danger')
    
    # Get usage data for display
    user_usage = QuotaManager.get_usage(tenant, ResourceType.USERS)
    storage_usage = QuotaManager.get_usage(tenant, ResourceType.STORAGE)
    
    tenant_data = {
        'id': tenant.id,
        'name': tenant.name,
        'slug': tenant.slug,
        'domain': tenant.domain,
        'description': tenant.description,
        'status': tenant.status,
        'plan': tenant.plan,
        'owner_email': tenant.owner_email,
        'quotas': {
            'max_users': tenant.max_users,
            'max_storage_mb': tenant.max_storage_mb
        },
        'usage': {
            'users': user_usage,
            'storage_mb': storage_usage,
            'users_percentage': QuotaManager.get_usage_percentage(tenant, ResourceType.USERS),
            'storage_percentage': QuotaManager.get_usage_percentage(tenant, ResourceType.STORAGE)
        }
    }
    
    return render_template('tenant/edit.html', 
                          title=f"Edit Tenant: {tenant.name}", 
                          tenant=tenant_data,
                          now=datetime.now())

@tenant_bp.route('/<slug>/status', methods=['POST'])
def update_status(slug):
    """Update tenant status"""
    # TODO: Add authorization check for admin
    
    tenant = Tenant.get_tenant_by_slug(slug)
    if not tenant:
        flash(f"Tenant '{slug}' not found", 'warning')
        return redirect(url_for('tenant.index'))
    
    # Get new status from form
    new_status = request.form.get('status')
    
    # Validate status
    valid_statuses = [
        TenantStatus.ACTIVE,
        TenantStatus.INACTIVE,
        TenantStatus.SUSPENDED
    ]
    
    if new_status not in valid_statuses:
        flash(f"Invalid status: {new_status}", 'danger')
        return redirect(url_for('tenant.view', slug=slug))
    
    try:
        # Update status based on the action
        if new_status == TenantStatus.ACTIVE:
            tenant.activate()
            flash(f"Tenant '{tenant.name}' activated", 'success')
        elif new_status == TenantStatus.INACTIVE:
            tenant.deactivate()
            flash(f"Tenant '{tenant.name}' deactivated", 'success')
        elif new_status == TenantStatus.SUSPENDED:
            tenant.suspend()
            flash(f"Tenant '{tenant.name}' suspended", 'success')
        
        return redirect(url_for('tenant.view', slug=slug))
        
    except Exception as e:
        logger.error(f"Error updating tenant status: {str(e)}")
        flash(f"Failed to update tenant status: {str(e)}", 'danger')
        return redirect(url_for('tenant.view', slug=slug))

@tenant_bp.route('/<slug>/delete', methods=['POST'])
def delete(slug):
    """Delete a tenant"""
    # TODO: Add authorization check for admin
    
    tenant = Tenant.get_tenant_by_slug(slug)
    if not tenant:
        flash(f"Tenant '{slug}' not found", 'warning')
        return redirect(url_for('tenant.index'))
    
    try:
        # Delete the tenant
        tenant_name = tenant.name
        tenant.delete()
        
        flash(f"Tenant '{tenant_name}' deleted successfully", 'success')
        return redirect(url_for('tenant.index'))
        
    except Exception as e:
        logger.error(f"Error deleting tenant: {str(e)}")
        flash(f"Failed to delete tenant: {str(e)}", 'danger')
        return redirect(url_for('tenant.view', slug=slug))

@tenant_bp.route('/<slug>/quota', methods=['GET'])
def quota(slug):
    """View tenant quota and usage"""
    # TODO: Add authorization check for admin or tenant owner
    
    tenant = Tenant.get_tenant_by_slug(slug)
    if not tenant:
        flash(f"Tenant '{slug}' not found", 'warning')
        return redirect(url_for('tenant.index'))
    
    # Get usage data
    user_usage = QuotaManager.get_usage(tenant, ResourceType.USERS)
    storage_usage = QuotaManager.get_usage(tenant, ResourceType.STORAGE)
    api_calls = QuotaManager.get_usage(tenant, ResourceType.API_CALLS)
    
    tenant_data = {
        'id': tenant.id,
        'name': tenant.name,
        'slug': tenant.slug,
        'plan': tenant.plan,
        'quotas': {
            'max_users': tenant.max_users,
            'max_storage_mb': tenant.max_storage_mb
        },
        'usage': {
            'users': user_usage,
            'storage_mb': storage_usage,
            'api_calls': api_calls,
            'users_percentage': QuotaManager.get_usage_percentage(tenant, ResourceType.USERS),
            'storage_percentage': QuotaManager.get_usage_percentage(tenant, ResourceType.STORAGE)
        }
    }
    
    return render_template('tenant/quota.html', 
                          title=f"Quota: {tenant.name}", 
                          tenant=tenant_data,
                          now=datetime.now())