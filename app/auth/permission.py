"""Permission definitions for role-based access control"""
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class Permission:
    """Permission class for defining access control"""
    
    # Tenant permissions
    VIEW_TENANT = 'view_tenant'
    CREATE_TENANT = 'create_tenant'
    EDIT_TENANT = 'edit_tenant'
    DELETE_TENANT = 'delete_tenant'
    
    # User permissions
    VIEW_USERS = 'view_users'
    CREATE_USER = 'create_user'
    EDIT_USER = 'edit_user'
    DELETE_USER = 'delete_user'
    
    # Role permissions
    VIEW_ROLES = 'view_roles'
    CREATE_ROLE = 'create_role'
    EDIT_ROLE = 'edit_role'
    DELETE_ROLE = 'delete_role'
    
    # Plugin permissions
    VIEW_PLUGINS = 'view_plugins'
    INSTALL_PLUGIN = 'install_plugin'
    UNINSTALL_PLUGIN = 'uninstall_plugin'
    CONFIGURE_PLUGIN = 'configure_plugin'
    
    # Admin permissions
    ADMIN_ACCESS = 'admin_access'
    SYSTEM_CONFIG = 'system_config'
    
    @classmethod
    def all_permissions(cls):
        """Get all available permissions"""
        permissions = []
        for attr_name in dir(cls):
            if not attr_name.startswith('_') and isinstance(getattr(cls, attr_name), str):
                permissions.append(getattr(cls, attr_name))
        return permissions
    
    @classmethod
    def get_permission_groups(cls):
        """Get permissions grouped by category"""
        return {
            'Tenant Permissions': [
                cls.VIEW_TENANT,
                cls.CREATE_TENANT,
                cls.EDIT_TENANT,
                cls.DELETE_TENANT
            ],
            'User Permissions': [
                cls.VIEW_USERS,
                cls.CREATE_USER,
                cls.EDIT_USER,
                cls.DELETE_USER
            ],
            'Role Permissions': [
                cls.VIEW_ROLES,
                cls.CREATE_ROLE,
                cls.EDIT_ROLE,
                cls.DELETE_ROLE
            ],
            'Plugin Permissions': [
                cls.VIEW_PLUGINS,
                cls.INSTALL_PLUGIN,
                cls.UNINSTALL_PLUGIN,
                cls.CONFIGURE_PLUGIN
            ],
            'Admin Permissions': [
                cls.ADMIN_ACCESS,
                cls.SYSTEM_CONFIG
            ]
        }