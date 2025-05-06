"""Plugin discovery, registration, and lifecycle management"""
from app import db
from app.plugins.plugin import Plugin, PluginStatus
from app.plugins.tenant_plugin import TenantPlugin
from app.tenant.tenant import Tenant
import importlib
import pkgutil
import logging
import os
import sys
import inspect

logger = logging.getLogger(__name__)

class PluginManager:
    """Manages plugin discovery, registration, and lifecycle"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(PluginManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the plugin manager"""
        if self._initialized:
            return
            
        self.plugins = {}
        self.plugin_instances = {}
        self._load_all_plugins()
        self._initialized = True
    
    def _load_all_plugins(self):
        """Load all registered plugins from the database"""
        for plugin in Plugin.query.all():
            self.plugins[plugin.slug] = plugin
    
    # def discover_plugins(self, plugins_dir='plugins'):
    #     """Discover plugins in the specified directory"""
    #     logger.info(f"Discovering plugins in {plugins_dir}")
        
    #     # Check if directory exists
    #     if not os.path.exists(plugins_dir):
    #         logger.error(f"Plugins directory does not exist: {plugins_dir}")
    #         return []
        
    #     # Log directory contents for debugging
    #     logger.info(f"Contents of {plugins_dir}:")
    #     try:
    #         for item in os.listdir(plugins_dir):
    #             logger.info(f"  - {item}")
    #     except Exception as e:
    #         logger.error(f"Error listing directory contents: {str(e)}")
        
    #     # Add plugins directory to Python path if not already there
    #     if plugins_dir not in sys.path:
    #         plugins_path = os.path.abspath(plugins_dir)
    #         sys.path.insert(0, plugins_path)
    #         logger.info(f"Added {plugins_path} to Python path")
        
    #     # Discover plugin modules
    #     discovered = []
    #     try:
    #         # Get list of module finders - this helps debug module finding issues
    #         module_paths = [plugins_dir]
    #         logger.info(f"Looking for modules in paths: {module_paths}")
            
    #         for finder, name, ispkg in pkgutil.iter_modules(module_paths):
    #             logger.info(f"Found module: {name}, is package: {ispkg}")
                
    #             if ispkg:  # Only consider packages, not individual modules
    #                 try:
    #                     # Import the plugin package
    #                     logger.info(f"Attempting to import {name}")
    #                     plugin_module = importlib.import_module(name)
                        
    #                     # Check if the module has a setup function
    #                     if hasattr(plugin_module, 'setup'):
    #                         logger.info(f"Module {name} has setup function")
    #                         metadata = plugin_module.setup()
    #                         discovered.append(metadata)
                            
    #                         # Register or update the plugin
    #                         Plugin.register_plugin(
    #                             name=metadata.get('name', name),
    #                             slug=metadata.get('slug', name.lower()),
    #                             version=metadata.get('version', '0.1.0'),
    #                             entry_point=metadata.get('entry_point', f"{name}:plugin"),
    #                             description=metadata.get('description'),
    #                             author=metadata.get('author'),
    #                             homepage=metadata.get('homepage'),
    #                             config_schema=metadata.get('config_schema'),
    #                             is_system=metadata.get('is_system', False),
    #                             enabled_for_all=metadata.get('enabled_for_all', False)
    #                         )
    #                         logger.info(f"Successfully registered plugin: {name}")
    #                     else:
    #                         logger.warning(f"Module {name} does not have a setup function")
                            
    #                 except Exception as e:
    #                     logger.error(f"Error loading plugin {name}: {str(e)}")
    #                     logger.error(f"Traceback: {traceback.format_exc()}")
    #     except Exception as e:
    #         logger.error(f"Error during module discovery: {str(e)}")
    #         logger.error(f"Traceback: {traceback.format_exc()}")
        
    #     # Reload plugins from the database
    #     self._load_all_plugins()
        
    #     logger.info(f"Discovered {len(discovered)} plugins: {[m.get('name') for m in discovered if isinstance(m, dict) and 'name' in m]}")
    #     return discovered
    def discover_plugins(self, plugins_dir='plugins'):
        """Discover plugins in the specified directory"""
        logger.info(f"Discovering plugins in {plugins_dir}")
        
        # Get absolute path to plugins directory
        if not os.path.isabs(plugins_dir):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            plugins_dir = os.path.join(base_dir, plugins_dir)
        
        logger.info(f"Using plugins directory: {plugins_dir}")
        
        # Check if directory exists
        if not os.path.exists(plugins_dir):
            logger.error(f"Plugins directory does not exist: {plugins_dir}")
            return []
        
        # Log directory contents for debugging
        logger.info(f"Contents of {plugins_dir}:")
        try:
            for item in os.listdir(plugins_dir):
                logger.info(f"  - {item}")
        except Exception as e:
            logger.error(f"Error listing directory contents: {str(e)}")
        
        # Add plugins directory to Python path if not already there
        if plugins_dir not in sys.path:
            sys.path.insert(0, plugins_dir)
            logger.info(f"Added {plugins_dir} to Python path")
        
        # Discover plugin modules
        discovered = []
        # Rest of the function remains the same...
        for item in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item)
            
            # Check if it's a directory (plugin package)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, '__init__.py')):
                try:
                    logger.info(f"Found potential plugin package: {item}")
                    
                    # Try to import the plugin package
                    # Fix: Use proper import name - the directory name should be the import name
                    plugin_module = importlib.import_module(item)
                    
                    # Check if it has a setup function
                    if hasattr(plugin_module, 'setup'):
                        logger.info(f"Module {item} has setup function")
                        try:
                            metadata = plugin_module.setup()
                            if metadata:
                                discovered.append(metadata)
                                
                                # Register or update the plugin
                                plugin = Plugin.register_plugin(
                                    name=metadata.get('name', item),
                                    slug=metadata.get('slug', item.lower()),
                                    version=metadata.get('version', '0.1.0'),
                                    entry_point=metadata.get('entry_point', f"{item}:plugin"),
                                    description=metadata.get('description'),
                                    author=metadata.get('author'),
                                    homepage=metadata.get('homepage'),
                                    config_schema=metadata.get('config_schema'),
                                    is_system=metadata.get('is_system', False),
                                    enabled_for_all=metadata.get('enabled_for_all', False)
                                )
                                logger.info(f"Successfully registered plugin: {metadata.get('name', item)}")
                            else:
                                logger.warning(f"Plugin {item} setup() function returned no metadata")
                        except Exception as e:
                            logger.error(f"Error in setup() function for {item}: {str(e)}")
                            import traceback
                            logger.error(f"Traceback: {traceback.format_exc()}")
                    else:
                        logger.warning(f"Module {item} does not have a setup function")
                        
                except Exception as e:
                    logger.error(f"Error loading plugin {item}: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Reload plugins from the database
        self._load_all_plugins()

        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered
    
    def activate_plugin(self, plugin_slug):
        """Activate a plugin"""
        plugin = Plugin.query.filter_by(slug=plugin_slug).first()
        if not plugin:
            logger.error(f"Plugin {plugin_slug} not found")
            return False
        
        try:
            # Log the current status
            logger.info(f"Activating plugin {plugin_slug}. Current status: {plugin.status}")
            
            # Test that we can load the plugin first
            plugin_class = plugin.load()
            if not plugin_class:
                logger.error(f"Failed to load plugin {plugin_slug}")
                return False
            
            # Initialize plugin instance and register its blueprint
            instance = plugin_class()
            
            # Register blueprint if the plugin provides one
            if hasattr(instance, 'get_blueprint'):
                from flask import current_app
                blueprint = instance.get_blueprint()
                if blueprint:
                    try:
                        # Check if blueprint is already registered
                        if blueprint.name not in current_app.blueprints:
                            current_app.register_blueprint(blueprint)
                            logger.info(f"Registered blueprint for plugin {plugin_slug}")
                    except Exception as e:
                        logger.error(f"Error registering blueprint for plugin {plugin_slug}: {str(e)}")
                        return False
            
            # Update status and immediately commit
            plugin.status = PluginStatus.ACTIVE.value
            db.session.commit()
            
            # Reload plugin and verify status
            db.session.refresh(plugin)
            if plugin.status != PluginStatus.ACTIVE.value:
                logger.error(f"Failed to update plugin status. Expected {PluginStatus.ACTIVE.value}, got {plugin.status}")
                return False
                    
            logger.info(f"Activated plugin: {plugin.name}")
            self.plugins[plugin_slug] = plugin  # Update the cached plugin in the manager
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error activating plugin {plugin_slug}: {str(e)}")
            return False

    def deactivate_plugin(self, plugin_slug):
        """Deactivate a plugin"""
        plugin = Plugin.query.filter_by(slug=plugin_slug).first()
        if not plugin:
            logger.error(f"Plugin {plugin_slug} not found")
            return False
        
        try:
            # Unregister blueprint if possible
            from flask import current_app
            blueprint_name = f"{plugin_slug}_blueprint"
            if blueprint_name in current_app.blueprints:
                # Flask doesn't have a built-in way to unregister blueprints,
                # but we can mark the plugin as inactive so it won't be used
                logger.info(f"Marking blueprint {blueprint_name} as inactive")
            
            plugin.status = PluginStatus.INACTIVE.value
            db.session.commit()
            
            # Reload plugin and verify status
            db.session.refresh(plugin)
            if plugin.status != PluginStatus.INACTIVE.value:
                logger.error(f"Failed to update plugin status. Expected {PluginStatus.INACTIVE.value}, got {plugin.status}")
                return False
                    
            logger.info(f"Deactivated plugin: {plugin.name}")
            
            # Remove any instances
            if plugin_slug in self.plugin_instances:
                del self.plugin_instances[plugin_slug]
            
            # Update the cached plugin
            self.plugins[plugin_slug] = plugin
            
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deactivating plugin {plugin_slug}: {str(e)}")
            return False
    
    
    def get_plugin_instance(self, plugin_slug, tenant_id=None):
        """Get an instance of the plugin for a specific tenant"""
        # Check if we already have an instance
        instance_key = f"{plugin_slug}:{tenant_id}" if tenant_id else plugin_slug
        if instance_key in self.plugin_instances:
            return self.plugin_instances[instance_key]
        
        # Get the plugin
        plugin = self.plugins.get(plugin_slug)
        if not plugin:
            # Try to get from database directly
            plugin = Plugin.query.filter_by(slug=plugin_slug).first()
            if plugin:
                self.plugins[plugin_slug] = plugin
            else:
                logger.error(f"Plugin {plugin_slug} not found")
                return None
        
        if plugin.status != PluginStatus.ACTIVE.value:
            logger.error(f"Plugin {plugin_slug} is not active. Current status: {plugin.status}")
            return None
        
        # Load the plugin
        plugin_class = plugin.load()
        if not plugin_class:
            return None
        
        # Get tenant-specific configuration if applicable
        config = {}
        if tenant_id:
            tenant_plugin = TenantPlugin.query.filter_by(
                tenant_id=tenant_id,
                plugin_id=plugin.id,
                enabled=True
            ).first()
            
            if tenant_plugin:
                config = tenant_plugin.config
            elif not plugin.enabled_for_all:
                logger.warning(f"Plugin {plugin_slug} is not enabled for tenant {tenant_id}")
                return None
        
        # Create an instance
        try:
            instance = plugin_class(config)
            self.plugin_instances[instance_key] = instance
            return instance
        except Exception as e:
            logger.error(f"Error instantiating plugin {plugin_slug}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def get_tenant_plugins(self, tenant_id):
        """Get all active plugins for a specific tenant"""
        # Get system-wide plugins that are enabled for all tenants
        system_plugins = Plugin.query.filter_by(
            status=PluginStatus.ACTIVE.value,
            enabled_for_all=True
        ).all()
        
        # Get tenant-specific plugins
        tenant_plugins = TenantPlugin.query.filter_by(
            tenant_id=tenant_id,
            enabled=True
        ).join(Plugin).filter(
            Plugin.status == PluginStatus.ACTIVE.value
        ).all()
        
        # Combine the results (exclude duplicates)
        system_plugin_ids = {p.id for p in system_plugins}
        result = list(system_plugins)
        
        for tp in tenant_plugins:
            if tp.plugin_id not in system_plugin_ids:
                result.append(tp.plugin)
        
        return result

    def load_plugin_blueprints(self, app):
        """Load and register blueprints for all active plugins"""
        try:
            from app.plugins.plugin import Plugin, PluginStatus
            
            # Get all active plugins
            active_plugins = Plugin.query.filter_by(status=PluginStatus.ACTIVE.value).all()
            
            for plugin in active_plugins:
                # Get plugin instance
                instance = self.get_plugin_instance(plugin.slug)
                
                if instance and hasattr(instance, 'get_blueprint'):
                    blueprint = instance.get_blueprint()
                    
                    if blueprint and blueprint.name not in app.blueprints:
                        app.register_blueprint(blueprint)
                        app.logger.info(f"Registered blueprint for plugin {plugin.slug}")
        except Exception as e:
            app.logger.error(f"Error loading plugin blueprints: {str(e)}")

def get_tenant_plugin_menu_items(self, tenant_id):
    """Get menu items for all active plugins for a tenant"""
    menu_items = []
    
    # Get all active plugins for this tenant
    plugins = self.get_tenant_plugins(tenant_id)
    
    for plugin in plugins:
        # Get plugin instance
        instance = self.get_plugin_instance(plugin.slug, tenant_id)
        if instance and hasattr(instance, 'get_menu_items'):
            try:
                items = instance.get_menu_items()
                if items:
                    menu_items.extend(items)
            except Exception as e:
                logger.error(f"Error getting menu items for plugin {plugin.slug}: {str(e)}")
    
    return menu_items