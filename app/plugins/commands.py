"""CLI commands for plugin management"""
import click
from flask.cli import with_appcontext
from app.plugins.plugin_manager import PluginManager
from app.plugins.plugin import Plugin, PluginStatus
from app.tenant.tenant import Tenant
from app.plugins.tenant_plugin import TenantPlugin
from app import db

@click.group()
def plugins_cli():
    """Plugin management commands."""
    pass

@plugins_cli.command('discover')
@with_appcontext
def discover_plugins():
    """Discover and register available plugins."""
    manager = PluginManager()
    plugins = manager.discover_plugins()
    click.echo(f"Discovered {len(plugins)} plugins.")
    for plugin in plugins:
        click.echo(f" - {plugin.get('name')} ({plugin.get('slug')})")

@plugins_cli.command('list')
@with_appcontext
def list_plugins():
    """List all registered plugins."""
    plugins = Plugin.query.all()
    click.echo(f"Found {len(plugins)} registered plugins:")
    for plugin in plugins:
        click.echo(f" - {plugin.name} ({plugin.slug}): {plugin.status}")

@plugins_cli.command('activate')
@click.argument('slug')
@with_appcontext
def activate_plugin(slug):
    """Activate a plugin."""
    plugin = Plugin.query.filter_by(slug=slug).first()
    if not plugin:
        click.echo(f"Plugin '{slug}' not found.")
        return
    
    click.echo(f"Current status of '{slug}': {plugin.status}")
    
    manager = PluginManager()
    success = manager.activate_plugin(slug)
    
    # Check status after activation attempt
    plugin = Plugin.query.filter_by(slug=slug).first()
    click.echo(f"Status after activation attempt: {plugin.status}")
    
    if success:
        click.echo(f"Plugin '{slug}' activated successfully.")
    else:
        click.echo(f"Failed to activate plugin '{slug}'.")

@plugins_cli.command('deactivate')
@click.argument('slug')
@with_appcontext
def deactivate_plugin(slug):
    """Deactivate a plugin."""
    manager = PluginManager()
    success = manager.deactivate_plugin(slug)
    if success:
        click.echo(f"Plugin '{slug}' deactivated successfully.")
    else:
        click.echo(f"Failed to deactivate plugin '{slug}'.")

@plugins_cli.command('enable-for-tenant')
@click.argument('plugin_slug')
@click.argument('tenant_slug')
@with_appcontext
def enable_for_tenant(plugin_slug, tenant_slug):
    """Enable a plugin for a specific tenant."""
    plugin = Plugin.query.filter_by(slug=plugin_slug).first()
    if not plugin:
        click.echo(f"Plugin '{plugin_slug}' not found.")
        return
    
    tenant = Tenant.query.filter_by(slug=tenant_slug).first()
    if not tenant:
        click.echo(f"Tenant '{tenant_slug}' not found.")
        return
    
    try:
        TenantPlugin.enable_for_tenant(tenant.id, plugin.id)
        click.echo(f"Plugin '{plugin_slug}' enabled for tenant '{tenant_slug}'.")
    except Exception as e:
        click.echo(f"Error enabling plugin: {str(e)}")

@plugins_cli.command('disable-for-tenant')
@click.argument('plugin_slug')
@click.argument('tenant_slug')
@with_appcontext
def disable_for_tenant(plugin_slug, tenant_slug):
    """Disable a plugin for a specific tenant."""
    plugin = Plugin.query.filter_by(slug=plugin_slug).first()
    if not plugin:
        click.echo(f"Plugin '{plugin_slug}' not found.")
        return
    
    tenant = Tenant.query.filter_by(slug=tenant_slug).first()
    if not tenant:
        click.echo(f"Tenant '{tenant_slug}' not found.")
        return
    
    try:
        success = TenantPlugin.disable_for_tenant(tenant.id, plugin.id)
        if success:
            click.echo(f"Plugin '{plugin_slug}' disabled for tenant '{tenant_slug}'.")
        else:
            click.echo(f"Plugin '{plugin_slug}' was not enabled for tenant '{tenant_slug}'.")
    except Exception as e:
        click.echo(f"Error disabling plugin: {str(e)}")

@plugins_cli.command('debug-plugin')
@click.argument('slug')
@with_appcontext
def debug_plugin(slug):
    """Debug a plugin's configuration and loading."""
    plugin = Plugin.query.filter_by(slug=slug).first()
    if not plugin:
        click.echo(f"Plugin '{slug}' not found.")
        return
    
    click.echo(f"Plugin Details:")
    click.echo(f"  ID: {plugin.id}")
    click.echo(f"  Name: {plugin.name}")
    click.echo(f"  Slug: {plugin.slug}")
    click.echo(f"  Status: {plugin.status}")
    click.echo(f"  Entry Point: {plugin.entry_point}")
    click.echo(f"  Module Path: {plugin.module_path}")
    click.echo(f"  Module Attr: {plugin.module_attr}")
    click.echo(f"  Is System: {plugin.is_system}")
    click.echo(f"  Enabled for All: {plugin.enabled_for_all}")
    
    # Test loading the plugin
    click.echo("\nAttempting to load plugin...")
    try:
        plugin_class = plugin.load()
        if plugin_class:
            click.echo(f"  SUCCESS: Plugin loaded successfully.")
            click.echo(f"  Plugin Class: {plugin_class}")
        else:
            click.echo(f"  FAILED: Plugin.load() returned None.")
    except Exception as e:
        click.echo(f"  ERROR: {str(e)}")
        import traceback
        click.echo(traceback.format_exc())
    
    # Get tenant assignments
    click.echo("\nTenant Assignments:")
    tenant_plugins = TenantPlugin.query.filter_by(plugin_id=plugin.id, enabled=True).all()
    if tenant_plugins:
        for tp in tenant_plugins:
            tenant = Tenant.query.get(tp.tenant_id)
            click.echo(f"  - {tenant.name} ({tenant.slug})")
    else:
        click.echo("  No tenants have this plugin enabled.")
    
    if plugin.enabled_for_all:
        click.echo("  Plugin is enabled for all tenants globally.")

def register_commands(app):
    """Register plugin management commands with Flask."""
    app.cli.add_command(plugins_cli)