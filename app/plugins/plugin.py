"""Plugin model and plugin management"""
from app import db
from app.core.db import BaseModel
from sqlalchemy.dialects.postgresql import JSONB
from enum import Enum
import importlib
import logging
import os
import sys
import json

logger = logging.getLogger(__name__)

class PluginStatus(Enum):
    """Plugin status enumeration"""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ERROR = 'error'
    PENDING = 'pending'

class Plugin(BaseModel):
    """Plugin model for registering available plugins"""
    __tablename__ = 'plugins'
    
    # Plugin identification
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    version = db.Column(db.String(20), nullable=False)
    
    # Plugin details
    description = db.Column(db.Text, nullable=True)
    author = db.Column(db.String(100), nullable=True)
    homepage = db.Column(db.String(255), nullable=True)
    
    # Plugin configuration
    entry_point = db.Column(db.String(255), nullable=False)
    config_schema = db.Column(JSONB, default={})
    
    # Plugin status
    status = db.Column(db.String(20), default=PluginStatus.PENDING.value)
    is_system = db.Column(db.Boolean, default=False)
    enabled_for_all = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Plugin {self.name} v{self.version}>'
    
    @property
    def module_path(self):
        """Get the module path for the plugin"""
        return self.entry_point.split(':')[0] if ':' in self.entry_point else self.entry_point
    
    @property
    def module_attr(self):
        """Get the module attribute/function for the plugin"""
        return self.entry_point.split(':')[1] if ':' in self.entry_point else 'plugin'
    
    def load(self):
        """Load the plugin module"""
        try:
            # Ensure the plugins directory is in the path
            plugins_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'plugins')
            if plugins_dir not in sys.path:
                sys.path.insert(0, plugins_dir)
                logger.info(f"Added plugins directory to sys.path in load(): {plugins_dir}")
                
            # Log detailed import information for debugging
            logger.info(f"Attempting to import module: {self.module_path}")
            logger.info(f"Module attribute: {self.module_attr}")
            logger.info(f"Current sys.path: {sys.path}")
            
            # Import the module
            module = importlib.import_module(self.module_path)
            
            # Get the plugin object/function
            if hasattr(module, self.module_attr):
                plugin_class = getattr(module, self.module_attr)
                logger.info(f"Successfully loaded plugin: {self.name}")
                return plugin_class
            else:
                logger.error(f"Plugin {self.name} doesn't have {self.module_attr} attribute")
                self.status = PluginStatus.ERROR.value
                db.session.commit()
                return None
                
        except Exception as e:
            logger.error(f"Failed to load plugin {self.name}: {str(e)}")
            self.status = PluginStatus.ERROR.value
            db.session.commit()
            return None
    
    @staticmethod
    def register_plugin(name, slug, version, entry_point, description=None, 
                        author=None, homepage=None, config_schema=None,
                        is_system=False, enabled_for_all=False):
        """Register a new plugin"""
        # Check if plugin already exists
        existing_plugin = Plugin.query.filter_by(slug=slug).first()
        if existing_plugin:
            # Update existing plugin
            existing_plugin.name = name
            existing_plugin.version = version
            existing_plugin.description = description
            existing_plugin.author = author
            existing_plugin.homepage = homepage
            existing_plugin.entry_point = entry_point
            existing_plugin.config_schema = config_schema or {}
            existing_plugin.is_system = is_system
            existing_plugin.enabled_for_all = enabled_for_all
            
            db.session.commit()
            logger.info(f"Updated plugin: {name} v{version}")
            return existing_plugin
        
        # Create new plugin
        plugin = Plugin(
            name=name,
            slug=slug,
            version=version,
            description=description,
            author=author,
            homepage=homepage,
            entry_point=entry_point,
            config_schema=config_schema or {},
            is_system=is_system,
            enabled_for_all=enabled_for_all,
            status=PluginStatus.INACTIVE.value
        )
        
        try:
            db.session.add(plugin)
            db.session.commit()
            logger.info(f"Registered plugin: {name} v{version}")
            return plugin
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering plugin {name}: {str(e)}")
            raise