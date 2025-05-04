from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from app import db
from app.plugins.plugin import Plugin, PluginStatus
from app.plugins.tenant_plugin import TenantPlugin
from app.plugins.plugin_manager import PluginManager
from app.auth.rbac import permission_required, system_admin_required
from app.tenant.middleware import tenant_required, get_current_tenant
import logging
import json

logger = logging.getLogger(__name__)

# Create blueprint
plugin_bp = Blueprint('plugins', __name__, url_prefix='/plugins')

@plugin_bp.route('/')
@permission_required('view_plugins')
def index():
    """Plugin management dashboard"""
    # Get current tenant
    tenant = get_current_tenant()
    
    # Get all plugins
    plugins = Plugin.query.all()
    
    # Get tenant plugins (if tenant context exists)
    tenant_plugins = []
    if tenant:
        # Get plugin manager
        plugin_manager = PluginManager()
        tenant_plugins = plugin_manager.get_tenant_plugins(tenant.id)
    
    return render_template('plugins/dashboard.html',
                          title='Plugin Management',
                          plugins=plugins,
                          tenant=tenant,
                          tenant_plugins=tenant_plugins)

@plugin_bp.route('/admin')
@system_admin_required
def admin():
    """Plugin administration for system admins"""
    # Get all plugins
    plugins = Plugin.query.all()
    
    return render_template('plugins/admin.html',
                          title='Plugin Administration',
                          plugins=plugins)

@plugin_bp.route('/discover', methods=['POST'])
@system_admin_required
def discover():
    """Discover and register new plugins"""
    # Get plugin manager
    plugin_manager = PluginManager()
    
    try:
        # Discover plugins
        discovered = plugin_manager.discover_plugins()
        
        if discovered:
            flash(f"Discovered {len(discovered)} plugins", 'success')
        else:
            flash("No new plugins found", 'info')
            
    except Exception as e:
        logger.error(f"Error discovering plugins: {str(e)}")
        flash(f"Error discovering plugins: {str(e)}", 'danger')
    
    return redirect(url_for('plugins.admin'))

@plugin_bp.route('/<slug>')
@permission_required('view_plugins')
def view(slug):
    """View plugin details"""
    # Get the plugin
    plugin = Plugin.query.filter_by(slug=slug).first()
    if not plugin:
        flash(f"Plugin '{slug}' not found", 'warning')
        return redirect(url_for('plugins.index'))
    
    # Get current tenant
    tenant = get_current_tenant()
    
    # Get tenant plugin configuration (if tenant context exists)
    tenant_plugin = None
    if tenant:
        tenant_plugin = TenantPlugin.query.filter_by(
            tenant_id=tenant.id,
            plugin_id=plugin.id
        ).first()
    
    # Get all tenants and enabled tenant ids for system admins
    tenants = []
    enabled_tenant_ids = []
    if current_user.is_system_admin:
        from app.tenant.tenant import Tenant
        tenants = Tenant.query.filter_by(status='active').all()
        tenant_plugins = TenantPlugin.query.filter_by(
            plugin_id=plugin.id,
            enabled=True
        ).all()
        enabled_tenant_ids = [tp.tenant_id for tp in tenant_plugins]
    
    # Debug information
    plugin_debug = {
        'id': plugin.id,
        'name': plugin.name,
        'slug': plugin.slug,
        'status': plugin.status,
        'entry_point': plugin.entry_point,
        'module_path': plugin.module_path,
        'module_attr': plugin.module_attr,
        'is_system': plugin.is_system,
        'enabled_for_all': plugin.enabled_for_all,
    }
    
    return render_template('plugins/view.html',
                          title=f"Plugin: {plugin.name}",
                          plugin=plugin,
                          tenant=tenant,
                          tenant_plugin=tenant_plugin,
                          tenants=tenants,
                          enabled_tenant_ids=enabled_tenant_ids,
                          plugin_debug=plugin_debug)
                          
@plugin_bp.route('/<slug>/assign-tenants', methods=['GET', 'POST'])
@system_admin_required
def assign_tenants(slug):
    """Assign plugin to multiple tenants"""
    # Get the plugin
    plugin = Plugin.query.filter_by(slug=slug).first()
    if not plugin:
        flash(f"Plugin '{slug}' not found", 'warning')
        return redirect(url_for('plugins.index'))
    
    # Check if plugin is active
    if plugin.status != PluginStatus.ACTIVE.value:
        flash(f"Plugin '{slug}' must be active before assigning to tenants", 'warning')
        return redirect(url_for('plugins.view', slug=slug))
    
    # Get all tenants
    from app.tenant.tenant import Tenant
    tenants = Tenant.query.filter_by(status='active').all()
    
    if request.method == 'POST':
        # Get form data
        tenant_ids = request.form.getlist('tenant_ids')
        enabled_for_all = request.form.get('enabled_for_all') == 'on'
        
        try:
            # Update plugin's enabled_for_all setting
            plugin.enabled_for_all = enabled_for_all
            db.session.commit()
            
            if not enabled_for_all:
                # Process tenant selections
                for tenant in tenants:
                    # Check if tenant is selected
                    if str(tenant.id) in tenant_ids:
                        # Enable plugin for this tenant
                        TenantPlugin.enable_for_tenant(tenant.id, plugin.id)
                    else:
                        # Disable plugin for this tenant
                        tenant_plugin = TenantPlugin.query.filter_by(
                            tenant_id=tenant.id,
                            plugin_id=plugin.id
                        ).first()
                        
                        if tenant_plugin and tenant_plugin.enabled:
                            TenantPlugin.disable_for_tenant(tenant.id, plugin.id)
            
            flash(f"Plugin '{plugin.name}' tenant assignments updated", 'success')
        except Exception as e:
            logger.error(f"Error assigning plugin to tenants: {str(e)}")
            flash(f"Error assigning plugin to tenants: {str(e)}", 'danger')
        
        return redirect(url_for('plugins.view', slug=slug))
    
    # Get currently enabled tenants for this plugin
    enabled_tenant_ids = []
    tenant_plugins = TenantPlugin.query.filter_by(
        plugin_id=plugin.id,
        enabled=True
    ).all()
    enabled_tenant_ids = [str(tp.tenant_id) for tp in tenant_plugins]
    
    return render_template('plugins/assign_tenants.html',
                          title=f"Assign Tenants - {plugin.name}",
                          plugin=plugin,
                          tenants=tenants,
                          enabled_tenant_ids=enabled_tenant_ids)

@plugin_bp.route('/<slug>/activate', methods=['POST'])
@system_admin_required
def activate(slug):
    """Activate a plugin"""
    # Get plugin manager
    plugin_manager = PluginManager()
    
    try:
        # Activate plugin
        success = plugin_manager.activate_plugin(slug)
        
        if success:
            flash(f"Plugin '{slug}' activated successfully", 'success')
        else:
            flash(f"Failed to activate plugin '{slug}'", 'danger')
            
    except Exception as e:
        logger.error(f"Error activating plugin: {str(e)}")
        flash(f"Error activating plugin: {str(e)}", 'danger')
    
    return redirect(url_for('plugins.admin'))

@plugin_bp.route('/<slug>/deactivate', methods=['POST'])
@system_admin_required
def deactivate(slug):
    """Deactivate a plugin"""
    # Get plugin manager
    plugin_manager = PluginManager()
    
    try:
        # Deactivate plugin
        success = plugin_manager.deactivate_plugin(slug)
        
        if success:
            flash(f"Plugin '{slug}' deactivated successfully", 'success')
        else:
            flash(f"Failed to deactivate plugin '{slug}'", 'danger')
            
    except Exception as e:
        logger.error(f"Error deactivating plugin: {str(e)}")
        flash(f"Error deactivating plugin: {str(e)}", 'danger')
    
    return redirect(url_for('plugins.admin'))

@plugin_bp.route('/<slug>/enable', methods=['POST'])
@permission_required('install_plugin')
@tenant_required
def enable(slug):
    """Enable a plugin for the current tenant"""
    # Get current tenant
    tenant = get_current_tenant()
    
    if not tenant:
        flash("No tenant context found", 'warning')
        return redirect(url_for('plugins.index'))
    
    # Get the plugin
    plugin = Plugin.query.filter_by(slug=slug).first()
    if not plugin:
        flash(f"Plugin '{slug}' not found", 'warning')
        return redirect(url_for('plugins.index'))
    
    # Check if plugin is active
    if plugin.status != PluginStatus.ACTIVE.value:
        flash(f"Plugin '{slug}' is not active", 'warning')
        return redirect(url_for('plugins.view', slug=slug))
    
    try:
        # Enable the plugin for tenant
        TenantPlugin.enable_for_tenant(tenant.id, plugin.id)
        
        flash(f"Plugin '{plugin.name}' enabled for tenant '{tenant.name}'", 'success')
            
    except Exception as e:
        logger.error(f"Error enabling plugin: {str(e)}")
        flash(f"Error enabling plugin: {str(e)}", 'danger')
    
    return redirect(url_for('plugins.view', slug=slug))

@plugin_bp.route('/<slug>/disable', methods=['POST'])
@permission_required('configure_plugin')
@tenant_required
def disable(slug):
    """Disable a plugin for the current tenant"""
    # Get current tenant
    tenant = get_current_tenant()
    
    if not tenant:
        flash("No tenant context found", 'warning')
        return redirect(url_for('plugins.index'))
    
    # Get the plugin
    plugin = Plugin.query.filter_by(slug=slug).first()
    if not plugin:
        flash(f"Plugin '{slug}' not found", 'warning')
        return redirect(url_for('plugins.index'))
    
    try:
        # Disable the plugin for tenant
        success = TenantPlugin.disable_for_tenant(tenant.id, plugin.id)
        
        if success:
            flash(f"Plugin '{plugin.name}' disabled for tenant '{tenant.name}'", 'success')
        else:
            flash(f"Plugin '{plugin.name}' was not enabled for tenant '{tenant.name}'", 'warning')
            
    except Exception as e:
        logger.error(f"Error disabling plugin: {str(e)}")
        flash(f"Error disabling plugin: {str(e)}", 'danger')
    
    return redirect(url_for('plugins.view', slug=slug))

@plugin_bp.route('/<slug>/config', methods=['GET', 'POST'])
@permission_required('configure_plugin')
@tenant_required
def configure(slug):
    """Configure a plugin for the current tenant"""
    # Get current tenant
    tenant = get_current_tenant()
    
    if not tenant:
        flash("No tenant context found", 'warning')
        return redirect(url_for('plugins.index'))
    
    # Get the plugin
    plugin = Plugin.query.filter_by(slug=slug).first()
    if not plugin:
        flash(f"Plugin '{slug}' not found", 'warning')
        return redirect(url_for('plugins.index'))
    
    # Get tenant plugin configuration
    tenant_plugin = TenantPlugin.query.filter_by(
        tenant_id=tenant.id,
        plugin_id=plugin.id
    ).first()
    
    if not tenant_plugin or not tenant_plugin.enabled:
        flash(f"Plugin '{plugin.name}' is not enabled for tenant '{tenant.name}'", 'warning')
        return redirect(url_for('plugins.view', slug=slug))
    
    if request.method == 'POST':
        try:
            # Get configuration from form
            config_json = request.form.get('config', '{}')
            config = json.loads(config_json)
            
            # Update configuration
            tenant_plugin.config = config
            db.session.commit()
            
            flash(f"Configuration for plugin '{plugin.name}' updated successfully", 'success')
            return redirect(url_for('plugins.view', slug=slug))
            
        except json.JSONDecodeError:
            flash("Invalid JSON configuration", 'danger')
        except Exception as e:
            logger.error(f"Error updating plugin configuration: {str(e)}")
            flash(f"Error updating plugin configuration: {str(e)}", 'danger')
    
    # Render configuration form
    return render_template('plugins/configure.html',
                          title=f"Configure Plugin: {plugin.name}",
                          plugin=plugin,
                          tenant=tenant,
                          tenant_plugin=tenant_plugin,
                          config_schema=plugin.config_schema)

@plugin_bp.route('/marketplace')
@permission_required('view_plugins')
def marketplace():
    """Plugin marketplace"""
    # Get all active plugins
    plugins = Plugin.query.filter_by(status=PluginStatus.ACTIVE.value).all()
    
    # Get current tenant
    tenant = get_current_tenant()
    
    # Create a map of enabled plugins for the tenant
    tenant_plugin_map = {}
    if tenant:
        tenant_plugins = TenantPlugin.query.filter_by(
            tenant_id=tenant.id,
            enabled=True
        ).all()
        tenant_plugin_map = {tp.plugin_id: True for tp in tenant_plugins}
    
    return render_template('plugins/marketplace.html',
                          title='Plugin Marketplace',
                          plugins=plugins,
                          tenant=tenant,
                          tenant_plugin_map=tenant_plugin_map)

@plugin_bp.route('/logs')
@permission_required('view_plugins')
def logs():
    """Plugin activity logs"""
    # Get current tenant
    tenant = get_current_tenant()
    
    # In a real implementation, you would retrieve logs from a database or log files
    # For this example, we'll just return an empty list
    logs = []
    
    return render_template('plugins/logs.html',
                          title='Plugin Logs',
                          logs=logs,
                          tenant=tenant)