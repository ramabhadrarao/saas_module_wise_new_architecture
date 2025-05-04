from app import db
from app.core.db import BaseModel
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
import uuid
import logging

logger = logging.getLogger(__name__)

class TenantStatus:
    """Enum for tenant status"""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'
    PROVISIONING = 'provisioning'
    DECOMMISSIONING = 'decommissioning'

class Tenant(BaseModel):
    """Tenant model for multi-tenant isolation"""
    __tablename__ = 'tenants'
    
    # Tenant identification
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    schema_name = db.Column(db.String(63), nullable=False, unique=True)
    
    # Tenant details
    description = db.Column(db.Text, nullable=True)
    domain = db.Column(db.String(253), nullable=True, unique=True)
    owner_email = db.Column(db.String(255), nullable=False)
    
    # Tenant status and metadata
    status = db.Column(db.String(20), default=TenantStatus.PROVISIONING)
    tenant_metadata = db.Column(JSONB, default={})  # Renamed from 'metadata' to 'tenant_metadata'
    
    # Resource limits and quotas
    max_users = db.Column(db.Integer, default=5)
    max_storage_mb = db.Column(db.Integer, default=100)
    
    # Billing information
    plan = db.Column(db.String(50), default='free')
    
    def __repr__(self):
        return f'<Tenant {self.name}>'
    
    @staticmethod
    def create_tenant(name, owner_email, description=None, domain=None, plan='free'):
        """Create a new tenant"""
        # Generate slug from name
        slug = name.lower().replace(' ', '-')
        
        # Generate schema name (must be valid PostgreSQL schema name)
        schema_name = f"tenant_{uuid.uuid4().hex[:16]}"
        
        # Create tenant record
        tenant = Tenant(
            name=name,
            slug=slug,
            schema_name=schema_name,
            description=description,
            domain=domain,
            owner_email=owner_email,
            plan=plan
        )
        
        try:
            db.session.add(tenant)
            db.session.commit()
            
            # Create tenant schema (will be implemented in schema_manager.py)
            from app.tenant.schema_manager import SchemaManager
            SchemaManager.create_schema(tenant.schema_name)
            
            # Set tenant to active after schema creation
            tenant.status = TenantStatus.ACTIVE
            db.session.commit()
            
            logger.info(f"Tenant created: {tenant.name} (schema: {tenant.schema_name})")
            return tenant
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating tenant: {str(e)}")
            raise
    
    @staticmethod
    def get_tenant_by_slug(slug):
        """Get tenant by slug"""
        return Tenant.query.filter_by(slug=slug).first()
    
    @staticmethod
    def get_tenant_by_domain(domain):
        """Get tenant by domain"""
        return Tenant.query.filter_by(domain=domain).first()
    
    def activate(self):
        """Activate a tenant"""
        if self.status != TenantStatus.ACTIVE:
            self.status = TenantStatus.ACTIVE
            db.session.commit()
            logger.info(f"Tenant activated: {self.name}")
    
    def deactivate(self):
        """Deactivate a tenant"""
        if self.status == TenantStatus.ACTIVE:
            self.status = TenantStatus.INACTIVE
            db.session.commit()
            logger.info(f"Tenant deactivated: {self.name}")
    
    def suspend(self):
        """Suspend a tenant"""
        if self.status != TenantStatus.SUSPENDED:
            self.status = TenantStatus.SUSPENDED
            db.session.commit()
            logger.info(f"Tenant suspended: {self.name}")
    
    def delete(self):
        """Mark tenant for deletion and trigger schema removal"""
        self.status = TenantStatus.DECOMMISSIONING
        db.session.commit()
        
        try:
            # Remove tenant schema (will be implemented in schema_manager.py)
            from app.tenant.schema_manager import SchemaManager
            SchemaManager.drop_schema(self.schema_name)
            
            # Delete tenant record
            db.session.delete(self)
            db.session.commit()
            logger.info(f"Tenant deleted: {self.name}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting tenant: {str(e)}")
            raise
    
    def update_quota(self, max_users=None, max_storage_mb=None):
        """Update tenant resource quotas"""
        if max_users is not None:
            self.max_users = max_users
        
        if max_storage_mb is not None:
            self.max_storage_mb = max_storage_mb
        
        db.session.commit()
        logger.info(f"Tenant quota updated: {self.name}")
    
    def update_plan(self, plan):
        """Update tenant subscription plan"""
        self.plan = plan
        db.session.commit()
        logger.info(f"Tenant plan updated: {self.name} to {plan}")