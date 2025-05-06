import os
from flask import Flask, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, current_user
import sys
import datetime
import traceback
import importlib

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page'
login_manager.login_message_category = 'warning'

# Function to register all plugin blueprints
def register_all_plugin_blueprints(app):
    """Register blueprints for all plugins during app initialization"""
    try:
        from app.plugins.plugin import Plugin
        from app.plugins.plugin_manager import PluginManager
        
        plugins = Plugin.query.all()
        for plugin in plugins:
            try:
                # Load the plugin class
                plugin_class = plugin.load()
                if plugin_class:
                    # Initialize the plugin
                    instance = plugin_class()
                    
                    # Register blueprint if the plugin provides one
                    if hasattr(instance, 'get_blueprint'):
                        blueprint = instance.get_blueprint()
                        if blueprint and blueprint.name not in app.blueprints:
                            app.register_blueprint(blueprint)
                            app.logger.info(f"Pre-registered blueprint for plugin {plugin.slug}")
            except Exception as e:
                app.logger.error(f"Error pre-registering blueprint for plugin {plugin.slug}: {str(e)}")
    except Exception as e:
        app.logger.error(f"Error registering all plugin blueprints: {str(e)}")

def create_app():
    """Application factory pattern for Flask app creation"""
    
    # Create and configure the app
    app = Flask(__name__)
    
    # Load configuration
    from app.core.config import config_by_name
    config_obj = config_by_name[os.getenv('FLASK_ENV', 'development')]
    app.config.from_object(config_obj)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Configure login manager
    from app.auth.user import User, AnonymousUser
    login_manager.anonymous_user = AnonymousUser
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register context processors
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.now()}
    
    # Add a context processor for plugin menu items
    @app.context_processor
    def inject_plugin_menu_items():
        """Inject plugin menu items into all templates"""
        from app.tenant.middleware import get_current_tenant
        from flask_login import current_user
        
        tenant = get_current_tenant()
        plugin_menu_items = []
        
        if tenant and current_user.is_authenticated:
            try:
                # Get active plugins for this tenant
                from app.plugins.plugin_manager import PluginManager
                plugin_manager = PluginManager()
                
                # Get menu items from each plugin
                plugins = plugin_manager.get_tenant_plugins(tenant.id)
                
                for plugin in plugins:
                    instance = plugin_manager.get_plugin_instance(plugin.slug, tenant.id)
                    if instance and hasattr(instance, 'get_menu_items'):
                        try:
                            items = instance.get_menu_items()
                            if items:
                                plugin_menu_items.extend(items)
                        except Exception as e:
                            app.logger.error(f"Error getting menu items for plugin {plugin.slug}: {str(e)}")
            except Exception as e:
                app.logger.error(f"Error getting plugin menu items: {str(e)}")
                import traceback
                app.logger.error(traceback.format_exc())
        
        return {'plugin_menu_items': plugin_menu_items}
    
    # Add to create_app() function after other context processors
    @app.context_processor
    def inject_plugin_context():
        """Inject plugin-related data into templates"""
        def get_tenant_active_plugins(tenant_id=None):
            if not tenant_id:
                return []
            
            try:
                from app.plugins.plugin_manager import PluginManager
                from app.plugins.tenant_plugin import TenantPlugin
                from app.plugins.plugin import Plugin, PluginStatus
                
                # Get tenant-specific plugins
                tenant_plugins = TenantPlugin.query.filter_by(
                    tenant_id=tenant_id,
                    enabled=True
                ).join(Plugin).filter(
                    Plugin.status == PluginStatus.ACTIVE.value
                ).all()
                
                # Get plugins enabled for all tenants
                global_plugins = Plugin.query.filter_by(
                    status=PluginStatus.ACTIVE.value,
                    enabled_for_all=True
                ).all()
                
                # Combine (avoiding duplicates)
                plugin_manager = PluginManager()
                results = []
                plugin_ids = set()
                
                # Process tenant-specific plugins
                for tp in tenant_plugins:
                    if tp.plugin_id not in plugin_ids:
                        plugin_ids.add(tp.plugin_id)
                        instance = plugin_manager.get_plugin_instance(tp.plugin.slug, tenant_id)
                        
                        if instance and hasattr(instance, 'get_menu_items'):
                            menu_items = instance.get_menu_items()
                            results.append({
                                'id': tp.plugin.id,
                                'name': tp.plugin.name,
                                'slug': tp.plugin.slug,
                                'menu_items': menu_items
                            })
                
                # Process global plugins
                for plugin in global_plugins:
                    if plugin.id not in plugin_ids:
                        instance = plugin_manager.get_plugin_instance(plugin.slug)
                        
                        if instance and hasattr(instance, 'get_menu_items'):
                            menu_items = instance.get_menu_items()
                            results.append({
                                'id': plugin.id,
                                'name': plugin.name,
                                'slug': plugin.slug,
                                'menu_items': menu_items
                            })
                
                return results
            except Exception as e:
                app.logger.error(f"Error fetching tenant plugins: {str(e)}")
                return []
        
        return {
            'get_tenant_active_plugins': get_tenant_active_plugins
        }
    
    @app.context_processor
    def plugin_utility_processor():
        """Add plugin utility functions to template context"""
        def empty_plugin_list(*args, **kwargs):
            return []
            
        try:
            from app.plugins.plugin_manager import PluginManager
            plugin_manager = PluginManager()
            return {
                'get_tenant_active_plugins': plugin_manager.get_tenant_plugins
            }
        except Exception as e:
            app.logger.warning(f"Unable to provide plugin utility functions: {str(e)}")
            return {
                'get_tenant_active_plugins': empty_plugin_list
            }
    
    @app.context_processor
    def inject_plugin_data():
        """Inject plugin data for templates"""
        def get_tenant_active_plugins(tenant_id=None):
            """Get active plugins for a tenant with their menu items"""
            if not tenant_id:
                return []
            
            try:
                from app.plugins.plugin_manager import PluginManager
                from app.tenant.tenant import Tenant
                from app.tenant.middleware import get_current_tenant
                from app.plugins.tenant_plugin import TenantPlugin
                from app.plugins.plugin import Plugin, PluginStatus
                
                # Get tenant plugins
                tenant_plugins = TenantPlugin.query.filter_by(
                    tenant_id=tenant_id,
                    enabled=True
                ).join(Plugin).filter(
                    Plugin.status == PluginStatus.ACTIVE.value
                ).all()
                
                # Get global plugins
                global_plugins = Plugin.query.filter_by(
                    status=PluginStatus.ACTIVE.value,
                    enabled_for_all=True
                ).all()
                
                # Combine them (avoiding duplicates)
                plugin_manager = PluginManager()
                result = []
                
                # Process tenant-specific plugins
                for tp in tenant_plugins:
                    instance = plugin_manager.get_plugin_instance(tp.plugin.slug, tenant_id)
                    if instance and hasattr(instance, 'get_menu_items'):
                        menu_items = instance.get_menu_items()
                        result.append({
                            'id': tp.plugin.id,
                            'name': tp.plugin.name,
                            'slug': tp.plugin.slug,
                            'menu_items': menu_items
                        })
                
                # Process global plugins (if not already added)
                plugin_slugs = {p['slug'] for p in result}
                for plugin in global_plugins:
                    if plugin.slug not in plugin_slugs:
                        instance = plugin_manager.get_plugin_instance(plugin.slug)
                        if instance and hasattr(instance, 'get_menu_items'):
                            menu_items = instance.get_menu_items()
                            result.append({
                                'id': plugin.id,
                                'name': plugin.name,
                                'slug': plugin.slug,
                                'menu_items': menu_items
                            })
                
                return result
            except Exception as e:
                current_app.logger.error(f"Error fetching tenant plugins: {str(e)}")
                return []
        
        return {
            'get_tenant_active_plugins': get_tenant_active_plugins
        }
    
    @app.before_request
    def require_login():
        # Public routes that don't require authentication
        public_paths = [
            '/auth/login', 
            '/auth/register',
            '/auth/reset-password',
            '/static/',
            '/health'
        ]
        
        # Allow access to public routes
        if any(request.path.startswith(path) for path in public_paths):
            return None
            
        # Redirect to login for all other routes if not authenticated
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
    
    # Register blueprints
    from app.core.views import main_bp
    app.register_blueprint(main_bp)
    
    # Register tenant blueprints
    try:
        from app.tenant.views import tenant_bp
        from app.tenant.routes import tenant_api
        app.register_blueprint(tenant_bp)
        app.register_blueprint(tenant_api)
    except ImportError:
        pass  # Tenant module not implemented yet
    
    # Register auth blueprints
    try:
        from app.auth.views import auth_bp
        from app.auth.routes import auth_api
        app.register_blueprint(auth_bp)
        app.register_blueprint(auth_api)
    except ImportError:
        pass  # Auth module not implemented yet
    
    # Register plugin blueprints
    try:
        from app.plugins.views import plugin_bp
        from app.plugins.routes import plugin_api
        app.register_blueprint(plugin_bp)
        app.register_blueprint(plugin_api)
    except ImportError:
        pass  # Plugin module not implemented yet
    
    # Register plugin commands
    try:
        from app.plugins.commands import register_commands
        register_commands(app)
        app.logger.info("Plugin CLI commands registered")
    except ImportError as e:
        app.logger.warning(f"Failed to register plugin commands: {str(e)}")
    
    # Register error handlers
    from app.core.error_handlers import register_handlers
    register_handlers(app)
    
    # Insert default roles
    with app.app_context():
        try:
            from app.auth.user import Role
            Role.insert_default_roles()
        except Exception as e:
            app.logger.error(f"Error inserting default roles: {str(e)}")
        
        # Initialize plugin manager - but only after checking if tables exist
        try:
            from sqlalchemy import inspect
            from app.plugins.plugin_manager import PluginManager
            
            # Check if plugins table exists before initializing
            inspector = inspect(db.engine)
            if 'plugins' in inspector.get_table_names():
                plugin_manager = PluginManager()
                
                # Register ALL plugin blueprints regardless of status
                register_all_plugin_blueprints(app)
                
                # Load active plugin data (no blueprint registration)
                plugin_manager.load_plugin_blueprints(app)
                app.logger.info("Plugin manager initialized successfully")
            else:
                app.logger.info("Plugins table not yet created - skipping plugin manager initialization")
        except Exception as e:
            app.logger.error(f"Error initializing plugin manager: {str(e)}")
    
    return app

# Create the application instance
app = create_app()