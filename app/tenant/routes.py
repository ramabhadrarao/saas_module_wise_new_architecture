from flask import Blueprint, request, jsonify, g, current_app
from app import db
from app.tenant.tenant import Tenant, TenantStatus
from app.tenant.quota import QuotaManager, ResourceType
from app.tenant.middleware import tenant_required, get_current_tenant
import logging

logger = logging.getLogger(__name__)

# Create blueprint
tenant_api = Blueprint('tenant_api', __name__, url_prefix='/api/tenant')

@tenant_api.route('/', methods=['GET'])
def list_tenants():
    """List all tenants (admin only)"""
    # TODO: Add authorization check for admin
    
    tenants = Tenant.query.all()
    result = []
    
    for tenant in tenants:
        result.append({
            'id': tenant.id,
            'name': tenant.name,
            'slug': tenant.slug,
            'domain': tenant.domain,
            'status': tenant.status,
            'plan': tenant.plan
        })
    
    return jsonify({
        'status': 'success',
        'data': result
    })

@tenant_api.route('/', methods=['POST'])
def create_tenant():
    """Create a new tenant"""
    # TODO: Add authorization check for admin or signup process
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'owner_email']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'status': 'error',
                'message': f"Missing required field: {field}"
            }), 400
    
    # Check if tenant with same name or domain already exists
    existing_tenant = Tenant.query.filter_by(name=data['name']).first()
    if existing_tenant:
        return jsonify({
            'status': 'error',
            'message': f"Tenant with name '{data['name']}' already exists"
        }), 400
    
    if data.get('domain'):
        existing_tenant = Tenant.query.filter_by(domain=data['domain']).first()
        if existing_tenant:
            return jsonify({
                'status': 'error',
                'message': f"Tenant with domain '{data['domain']}' already exists"
            }), 400
    
    try:
        # Create the tenant
        tenant = Tenant.create_tenant(
            name=data['name'],
            owner_email=data['owner_email'],
            description=data.get('description'),
            domain=data.get('domain'),
            plan=data.get('plan', 'free')
        )
        
        # Return tenant data
        return jsonify({
            'status': 'success',
            'message': f"Tenant '{tenant.name}' created successfully",
            'data': {
                'id': tenant.id,
                'name': tenant.name,
                'slug': tenant.slug,
                'schema_name': tenant.schema_name,
                'domain': tenant.domain,
                'status': tenant.status,
                'plan': tenant.plan
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating tenant: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to create tenant: {str(e)}"
        }), 500

@tenant_api.route('/<slug>', methods=['GET'])
def get_tenant(slug):
    """Get tenant details by slug"""
    # TODO: Add authorization check
    
    tenant = Tenant.get_tenant_by_slug(slug)
    if not tenant:
        return jsonify({
            'status': 'error',
            'message': f"Tenant '{slug}' not found"
        }), 404
    
    # Get usage data
    user_usage = QuotaManager.get_usage(tenant, ResourceType.USERS)
    storage_usage = QuotaManager.get_usage(tenant, ResourceType.STORAGE)
    
    # Return tenant data
    return jsonify({
        'status': 'success',
        'data': {
            'id': tenant.id,
            'name': tenant.name,
            'slug': tenant.slug,
            'domain': tenant.domain,
            'description': tenant.description,
            'status': tenant.status,
            'plan': tenant.plan,
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
    })

@tenant_api.route('/<slug>', methods=['PUT', 'PATCH'])
def update_tenant(slug):
    """Update tenant details"""
    # TODO: Add authorization check
    
    tenant = Tenant.get_tenant_by_slug(slug)
    if not tenant:
        return jsonify({
            'status': 'error',
            'message': f"Tenant '{slug}' not found"
        }), 404
    
    data = request.get_json()
    
    # Update allowed fields
    if 'name' in data:
        tenant.name = data['name']
    
    if 'description' in data:
        tenant.description = data['description']
    
    if 'domain' in data:
        # Check if domain is already used by another tenant
        existing_tenant = Tenant.query.filter_by(domain=data['domain']).first()
        if existing_tenant and existing_tenant.id != tenant.id:
            return jsonify({
                'status': 'error',
                'message': f"Domain '{data['domain']}' is already used by another tenant"
            }), 400
        tenant.domain = data['domain']
    
    if 'plan' in data:
        tenant.plan = data['plan']
    
    if 'max_users' in data:
        tenant.max_users = data['max_users']
    
    if 'max_storage_mb' in data:
        tenant.max_storage_mb = data['max_storage_mb']
    
    try:
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f"Tenant '{tenant.name}' updated successfully",
            'data': {
                'id': tenant.id,
                'name': tenant.name,
                'slug': tenant.slug,
                'domain': tenant.domain,
                'status': tenant.status,
                'plan': tenant.plan
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating tenant: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to update tenant: {str(e)}"
        }), 500

@tenant_api.route('/<slug>/status', methods=['PATCH'])
def update_tenant_status(slug):
    """Update tenant status"""
    # TODO: Add authorization check for admin
    
    tenant = Tenant.get_tenant_by_slug(slug)
    if not tenant:
        return jsonify({
            'status': 'error',
            'message': f"Tenant '{slug}' not found"
        }), 404
    
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({
            'status': 'error',
            'message': "Missing status field"
        }), 400
    
    new_status = data['status']
    
    # Validate status
    valid_statuses = [
        TenantStatus.ACTIVE,
        TenantStatus.INACTIVE,
        TenantStatus.SUSPENDED
    ]
    
    if new_status not in valid_statuses:
        return jsonify({
            'status': 'error',
            'message': f"Invalid status: {new_status}. Valid values are: {', '.join(valid_statuses)}"
        }), 400
    
    try:
        # Update status
        tenant.status = new_status
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f"Tenant status updated to '{new_status}'",
            'data': {
                'id': tenant.id,
                'name': tenant.name,
                'status': tenant.status
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating tenant status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to update tenant status: {str(e)}"
        }), 500

@tenant_api.route('/<slug>', methods=['DELETE'])
def delete_tenant(slug):
    """Delete a tenant"""
    # TODO: Add authorization check for admin
    
    tenant = Tenant.get_tenant_by_slug(slug)
    if not tenant:
        return jsonify({
            'status': 'error',
            'message': f"Tenant '{slug}' not found"
        }), 404
    
    try:
        # Delete the tenant
        tenant_name = tenant.name
        tenant.delete()
        
        return jsonify({
            'status': 'success',
            'message': f"Tenant '{tenant_name}' deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting tenant: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to delete tenant: {str(e)}"
        }), 500

@tenant_api.route('/current', methods=['GET'])
def get_current_tenant_info():
    """Get information about the current tenant"""
    tenant = get_current_tenant()
    
    if not tenant:
        return jsonify({
            'status': 'error',
            'message': "No tenant context found"
        }), 404
    
    # Get usage data
    user_usage = QuotaManager.get_usage(tenant, ResourceType.USERS)
    storage_usage = QuotaManager.get_usage(tenant, ResourceType.STORAGE)
    
    return jsonify({
        'status': 'success',
        'data': {
            'id': tenant.id,
            'name': tenant.name,
            'slug': tenant.slug,
            'domain': tenant.domain,
            'status': tenant.status,
            'plan': tenant.plan,
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
    })