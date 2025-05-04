import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

def create_app(config_name=None):
    """Application factory pattern for Flask app creation"""
    
    # Create and configure the app
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Load configuration
    from app.core.config import config_by_name
    config_obj = config_by_name[config_name or os.getenv('FLASK_ENV', 'development')]
    app.config.from_object(config_obj)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register shell context
    register_shell_context(app)
    
    return app

def register_blueprints(app):
    """Register Flask blueprints"""
    # Import and register the main blueprint
    from app.core.views import main_bp
    app.register_blueprint(main_bp)
    
    # Additional blueprints will be registered by the plugin system

def register_shell_context(app):
    """Register shell context objects"""
    def shell_context():
        return {
            'app': app,
            'db': db
        }
    
    app.shell_context_processor(shell_context)