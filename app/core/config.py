import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-key-please-change')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 
                                     'postgresql://saas_admin:Nihita!1981@localhost:5432/saas_main_db')
    
    # Application
    APP_NAME = "Multi-Tenant SaaS Platform"
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')
    
    # Logging
    LOG_LEVEL = 'INFO'
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # True if using HTTPS
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = False

    
    @staticmethod
    def init_app(app):
        """Initialize application with this configuration"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        """Initialize production application"""
        Config.init_app(app)
        
        # Configure production-specific logging
        import logging
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler('logs/saas.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

# Configuration dictionary
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}