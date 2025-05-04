"""API endpoints for plugin management"""
from flask import Blueprint, request, jsonify, g, current_app
from app import db
from app.plugins.plugin import Plugin, PluginStatus
from app.plugins.tenant_plugin import TenantPlugin
from app.plugins.plugin_manager import PluginManager
from app.auth.rbac import permission_required, system_admin_required
from app.tenant.middleware import tenant_required, get_current_tenant
import logging

logger = logging.getLogger(__name__)

# Create blueprint
plugin_api = Blueprint('plugin_api', __name__, url_prefix='/api/plugins')

@plugin_api.route('/', methods=['GET'])
@permission_required('view_plugins')
def list_plugins():
    """List all available plugins"""
    # Get all plugins
    plugins = Plugin.query.all()
    result = []
    
    for plugin in plugins:
        result.append({
            'id': plugin.id,
            'name': plugin.name,
            'slug': plugin.slug,
            'version': plugin.version,
            'description': plugin.description,
            'author': plugin.author,
            'homepage': plugin.homepage,
            'status': plugin.status,
            'is_system': plugin.is_system,
            'enabled_for_all': plugin.enabled_for_all
        })
    
    return jsonify({
        'status': 'success',
        'data': result
    })

@plugin_api.route('/tenant', methods=['GET'])
@permission_required('view_plugins')
@tenant_required
def list_tenant_plugins():
    """List all plugins for current tenant"""
    tenant = get_current_tenant()
    
    if not tenant:
        return jsonify({
            'status': 'error',
            'message': "No tenant context found"
        }), 404
    
    # Get plugins for tenant
    plugin_manager = PluginManager()
    plugins = plugin_manager.get_tenant_plugins(tenant.id)
    
    result = []
    for plugin in plugins:
        # Get tenant-specific configuration
        tenant_plugin = TenantPlugin.query.filter_by(
            tenant_id=tenant.id,
            plugin_id=plugin.id
        ).first()
        
        result.append({
            'id': plugin.id,
            'name': plugin.name,
            'slug': plugin.slug,
            'version': plugin.version,
            'description': plugin.description,
            'author': plugin.author,
            'status': plugin.status,
            'enabled': True,
            'config': tenant_plugin.config if tenant_plugin else {}
        })
    
    return jsonify({
        'status': 'success',
        'data': result
    })

@plugin_api.route('/discover', methods=['POST'])
@system_admin_required
def discover_plugins():
    """Discover and register new plugins"""
    plugin_manager = PluginManager()
    discovered = plugin_manager.discover_plugins()
    
    return jsonify({
        'status': 'success',
        'message': f"Discovered {len(discovered)} plugins",
        'data': discovered
    })

@plugin_api.route('/<slug>/activate', methods=['POST'])
@system_admin_required
def activate_plugin(slug):
    """Activate a plugin"""
    plugin_manager = PluginManager()
    success = plugin_manager.activate_plugin(slug)
    
    if success:
        return jsonify({
            'status': 'success',
            'message': f"Plugin '{slug}' activated successfully"
        })
    else:
        return jsonify({
            'status': 'error',
            'message': f"Failed to activate plugin '{slug}'"
        }), 400

@plugin_api.route('/<slug>/deactivate', methods=['POST'])
@system_admin_required
def deactivate_plugin(slug):
    """Deactivate a plugin"""
    plugin_manager = PluginManager()
    success = plugin_manager.deactivate_plugin(slug)
    
    if success:
        return jsonify({
            'status': 'success',
            'message': f"Plugin '{slug}' deactivated successfully"
        })
    else:
        return jsonify({
            'status': 'error',
            'message': f"Failed to deactivate plugin '{slug}'"
        }), 400

@plugin_api.route('/tenant/<plugin_slug>/enable', methods=['POST'])
@permission_required('install_plugin')
@tenant_required
def enable_for_tenant(plugin_slug):
    """Enable a plugin for the current tenant"""
    tenant = get_current_tenant()
    
    if not tenant:
        return jsonify({
            'status': 'error',
            'message': "No tenant context found"
        }), 404
    
    # Get the plugin
    plugin = Plugin.query.filter_by(slug=plugin_slug).first()
    if not plugin:
        return jsonify({
            'status': 'error',
            'message': f"Plugin '{plugin_slug}' not found"
        }), 404
    
    # Check if plugin is active
    if plugin.status != PluginStatus.ACTIVE.value:
        return jsonify({
            'status': 'error',
            'message': f"Plugin '{plugin_slug}' is not active"
        }), 400
    
    # Get configuration from request
    data = request.get_json() or {}
    config = data.get('config', {})
    
    try:
        # Enable the plugin for tenant
        TenantPlugin.enable_for_tenant(tenant.id, plugin.id, config)
        
        return jsonify({
            'status': 'success',
            'message': f"Plugin '{plugin_slug}' enabled for tenant '{tenant.name}'"
        })
        
    except Exception as e:
        logger.error(f"Error enabling plugin: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to enable plugin: {str(e)}"
        }), 500

@plugin_api.route('/tenant/<plugin_slug>/disable', methods=['POST'])
@permission_required('configure_plugin')
@tenant_required
def disable_for_tenant(plugin_slug):
    """Disable a plugin for the current tenant"""
    tenant = get_current_tenant()
    
    if not tenant:
        return jsonify({
            'status': 'error',
            'message': "No tenant context found"
        }), 404
    
    # Get the plugin
    plugin = Plugin.query.filter_by(slug=plugin_slug).first()
    if not plugin:
        return jsonify({
            'status': 'error',
            'message': f"Plugin '{plugin_slug}' not found"
        }), 404
    
    try:
        # Disable the plugin for tenant
        success = TenantPlugin.disable_for_tenant(tenant.id, plugin.id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f"Plugin '{plugin_slug}' disabled for tenant '{tenant.name}'"
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Plugin '{plugin_slug}' was not enabled for tenant '{tenant.name}'"
            }), 400
        
    except Exception as e:
        logger.error(f"Error disabling plugin: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to disable plugin: {str(e)}"
        }), 500

@plugin_api.route('/tenant/<plugin_slug>/config', methods=['PUT'])
@permission_required('configure_plugin')
@tenant_required
def update_tenant_plugin_config(plugin_slug):
    """Update plugin configuration for the current tenant"""
    tenant = get_current_tenant()
    
    if not tenant:
        return jsonify({
            'status': 'error',
            'message': "No tenant context found"
        }), 404
    
    # Get the plugin
    plugin = Plugin.query.filter_by(slug=plugin_slug).first()
    if not plugin:
        return jsonify({
            'status': 'error',
            'message': f"Plugin '{plugin_slug}' not found"
        }), 404
    
    # Get configuration from request
    data = request.get_json()
    if not data:
        return jsonify({
            'status': 'error',
            'message': "No configuration provided"
        }), 400
    
    # Get tenant plugin association
    tenant_plugin = TenantPlugin.query.filter_by(
        tenant_id=tenant.id,
        plugin_id=plugin.id
    ).first()
    
    if not tenant_plugin:
        return jsonify({
            'status': 'error',
            'message': f"Plugin '{plugin_slug}' is not enabled for tenant '{tenant.name}'"
        }), 400
    
    try:
        # Update configuration
        tenant_plugin.config = data
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f"Configuration for plugin '{plugin_slug}' updated successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating plugin configuration: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to update plugin configuration: {str(e)}"
        }), 500