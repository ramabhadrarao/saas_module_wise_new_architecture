"""Tenant-plugin association for managing enabled plugins per tenant"""
from app import db
from app.core.db import BaseModel
from sqlalchemy.dialects.postgresql import JSONB
import logging

logger = logging.getLogger(__name__)

class TenantPlugin(BaseModel):
    """Tenant-plugin association for managing enabled plugins per tenant"""
    __tablename__ = 'tenant_plugins'
    
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    plugin_id = db.Column(db.Integer, db.ForeignKey('plugins.id'), nullable=False)
    
    # Plugin configuration for this tenant
    enabled = db.Column(db.Boolean, default=True)
    config = db.Column(JSONB, default={})
    
    # Relationships
    tenant = db.relationship('Tenant', backref=db.backref('plugin_configs', lazy='dynamic'))
    plugin = db.relationship('Plugin', backref=db.backref('tenant_configs', lazy='dynamic'))
    
    # Composite unique constraint
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'plugin_id', name='uq_tenant_plugin'),
    )
    
    def __repr__(self):
        return f'<TenantPlugin {self.tenant.name} - {self.plugin.name}>'
    
    @staticmethod
    def enable_for_tenant(tenant_id, plugin_id, config=None):
        """Enable a plugin for a specific tenant"""
        tenant_plugin = TenantPlugin.query.filter_by(
            tenant_id=tenant_id, 
            plugin_id=plugin_id
        ).first()
        
        if tenant_plugin:
            # Update existing configuration
            tenant_plugin.enabled = True
            if config:
                tenant_plugin.config = config
        else:
            # Create new tenant-plugin association
            tenant_plugin = TenantPlugin(
                tenant_id=tenant_id,
                plugin_id=plugin_id,
                enabled=True,
                config=config or {}
            )
            db.session.add(tenant_plugin)
        
        try:
            db.session.commit()
            logger.info(f"Enabled plugin (ID: {plugin_id}) for tenant (ID: {tenant_id})")
            return tenant_plugin
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error enabling plugin: {str(e)}")
            raise
    
    @staticmethod
    def disable_for_tenant(tenant_id, plugin_id):
        """Disable a plugin for a specific tenant"""
        tenant_plugin = TenantPlugin.query.filter_by(
            tenant_id=tenant_id, 
            plugin_id=plugin_id
        ).first()
        
        if tenant_plugin:
            tenant_plugin.enabled = False
            
            try:
                db.session.commit()
                logger.info(f"Disabled plugin (ID: {plugin_id}) for tenant (ID: {tenant_id})")
                return True
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error disabling plugin: {str(e)}")
                raise
        
        return False
    
    @staticmethod
    def get_tenant_plugins(tenant_id, include_disabled=False):
        """Get all plugins for a specific tenant"""
        query = TenantPlugin.query.filter_by(tenant_id=tenant_id)
        
        if not include_disabled:
            query = query.filter_by(enabled=True)
        
        return query.all()