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

# plugins_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins')
# if plugins_path not in sys.path:
#     sys.path.insert(0, plugins_path)

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
    
    # Add authentication middleware
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
        # # Debug plugin discovery
        # try:
        #     from sqlalchemy import inspect
        #     inspector = inspect(db.engine)
        #     app.logger.info(f"Available tables: {inspector.get_table_names()}")
            
        #     # Check if plugins table exists
        #     if 'plugins' in inspector.get_table_names():
        #         app.logger.info("Plugins table exists in database")
                
        #         # Check if paths are correct
        #         import os
        #         project_root = os.path.dirname(os.path.dirname(__file__))
        #         plugins_dir = os.path.join(project_root, 'plugins')
        #         app.logger.info(f"Project root: {project_root}")
        #         app.logger.info(f"Plugins directory: {plugins_dir}")
        #         app.logger.info(f"Plugins directory exists: {os.path.exists(plugins_dir)}")
                
        #         if os.path.exists(plugins_dir):
        #             app.logger.info(f"Plugins directory contents: {os.listdir(plugins_dir)}")
        #     else:
        #         app.logger.warning("Plugins table does not exist in database")
        # except Exception as e:
        #     app.logger.error(f"Error debugging plugin discovery: {str(e)}")
        # Initialize plugin manager - but only after checking if tables exist
        try:
            from sqlalchemy import inspect
            from app.plugins.plugin_manager import PluginManager
            
            # Check if plugins table exists before initializing
            inspector = inspect(db.engine)
            if 'plugins' in inspector.get_table_names():
                plugin_manager = PluginManager()
                app.logger.info("Plugin manager initialized successfully")
            else:
                app.logger.info("Plugins table not yet created - skipping plugin manager initialization")
        except Exception as e:
            app.logger.error(f"Error initializing plugin manager: {str(e)}")
    
    return app

# Create the application instance
app = create_app()