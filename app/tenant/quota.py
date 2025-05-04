from app import db
from app.core.db import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TenantUsage(BaseModel):
    """Track resource usage for tenants"""
    __tablename__ = 'tenant_usage'
    
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    usage_amount = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    tenant = db.relationship('Tenant', backref=db.backref('usage_records', lazy='dynamic'))
    
    # Composite unique constraint
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'resource_type', name='uq_tenant_resource'),
    )
    
    def __repr__(self):
        return f'<TenantUsage {self.tenant.name} - {self.resource_type}: {self.usage_amount}>'

class ResourceType:
    """Resource types for quota tracking"""
    USERS = 'users'
    STORAGE = 'storage_mb'
    API_CALLS = 'api_calls'

class QuotaManager:
    """Manage tenant resource quotas and usage"""
    
    @staticmethod
    def get_usage(tenant, resource_type):
        """Get current resource usage for a tenant"""
        usage = TenantUsage.query.filter_by(
            tenant_id=tenant.id,
            resource_type=resource_type
        ).first()
        
        if not usage:
            # Create new usage record if none exists
            usage = TenantUsage(
                tenant_id=tenant.id,
                resource_type=resource_type,
                usage_amount=0
            )
            db.session.add(usage)
            db.session.commit()
        
        return usage.usage_amount
    
    @staticmethod
    def update_usage(tenant, resource_type, amount):
        """Update resource usage for a tenant"""
        usage = TenantUsage.query.filter_by(
            tenant_id=tenant.id,
            resource_type=resource_type
        ).first()
        
        if not usage:
            # Create new usage record if none exists
            usage = TenantUsage(
                tenant_id=tenant.id,
                resource_type=resource_type,
                usage_amount=amount
            )
            db.session.add(usage)
        else:
            # Update existing record
            usage.usage_amount = amount
        
        db.session.commit()
        logger.info(f"Updated {resource_type} usage for {tenant.name}: {amount}")
    
    @staticmethod
    def increment_usage(tenant, resource_type, increment=1):
        """Increment resource usage for a tenant"""
        usage = TenantUsage.query.filter_by(
            tenant_id=tenant.id,
            resource_type=resource_type
        ).first()
        
        if not usage:
            # Create new usage record if none exists
            usage = TenantUsage(
                tenant_id=tenant.id,
                resource_type=resource_type,
                usage_amount=increment
            )
            db.session.add(usage)
        else:
            # Increment existing record
            usage.usage_amount += increment
        
        db.session.commit()
        logger.info(f"Incremented {resource_type} usage for {tenant.name} by {increment}")
        return usage.usage_amount
    
    @staticmethod
    def check_quota_available(tenant, resource_type, amount=1):
        """Check if tenant has quota available for a specific resource"""
        current_usage = QuotaManager.get_usage(tenant, resource_type)
        
        if resource_type == ResourceType.USERS:
            limit = tenant.max_users
        elif resource_type == ResourceType.STORAGE:
            limit = tenant.max_storage_mb
        else:
            # No limit defined for this resource type
            return True
        
        # Check if quota is exceeded
        return (current_usage + amount) <= limit
    
    @staticmethod
    def get_usage_percentage(tenant, resource_type):
        """Get percentage of quota used for a specific resource"""
        current_usage = QuotaManager.get_usage(tenant, resource_type)
        
        if resource_type == ResourceType.USERS:
            limit = tenant.max_users
        elif resource_type == ResourceType.STORAGE:
            limit = tenant.max_storage_mb
        else:
            # No limit defined for this resource type
            return 0
        
        if limit <= 0:
            return 100  # Avoid division by zero
        
        return min(int((current_usage / limit) * 100), 100)  # Cap at 100%