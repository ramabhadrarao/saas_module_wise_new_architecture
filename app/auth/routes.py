"""API endpoints for authentication and authorization"""
from flask import Blueprint, request, jsonify, g, current_app
from app import db
from app.auth.user import User, Role
from app.tenant.tenant import Tenant
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required
import logging

logger = logging.getLogger(__name__)

# Create blueprint
auth_api = Blueprint('auth_api', __name__, url_prefix='/api/auth')

@auth_api.route('/login', methods=['POST'])
def login():
    """Login API endpoint"""
    data = request.get_json()
    
    # Validate input
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({
            'status': 'error',
            'message': 'Username and password are required'
        }), 400
    
    # Find user by username or email
    username = data.get('username')
    user = User.query.filter((User.username == username) | (User.email == username)).first()
    
    if user is None or not user.verify_password(data.get('password')):
        return jsonify({
            'status': 'error',
            'message': 'Invalid username or password'
        }), 401
    
    if not user.is_active:
        return jsonify({
            'status': 'error',
            'message': 'This account is inactive'
        }), 403
    
    # Check tenant status if user belongs to a tenant
    if user.tenant_id:
        tenant = Tenant.query.get(user.tenant_id)
        if tenant and tenant.status != 'active':
            return jsonify({
                'status': 'error',
                'message': f"Your tenant '{tenant.name}' is {tenant.status}"
            }), 403
    
    # Update last login time
    user.update_last_login()
    
    # Generate authentication token
    token = user.generate_auth_token()
    
    return jsonify({
        'status': 'success',
        'message': 'Login successful',
        'data': {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'tenant_id': user.tenant_id,
            'is_tenant_admin': user.is_tenant_admin,
            'is_system_admin': user.is_system_admin,
            'token': token
        }
    })

@auth_api.route('/register', methods=['POST'])
def register():
    """Register API endpoint"""
    data = request.get_json()
    
    # Validate input
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'status': 'error',
                'message': f"Missing required field: {field}"
            }), 400
    
    # Check if username or email already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({
            'status': 'error',
            'message': f"Username '{data['username']}' is already taken"
        }), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({
            'status': 'error',
            'message': f"Email '{data['email']}' is already registered"
        }), 400
    
    try:
        # Create new user
        user = User.create_user(
            email=data['email'],
            username=data['username'],
            password=data['password'],
            tenant_id=data.get('tenant_id'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            is_tenant_admin=data.get('is_tenant_admin', False),
            is_system_admin=data.get('is_system_admin', False)
        )
        
        # Add default user role
        user_role = Role.query.filter_by(name='User').first()
        if user_role:
            user.roles.append(user_role)
            db.session.commit()
        
        # Generate authentication token
        token = user.generate_auth_token()
        
        return jsonify({
            'status': 'success',
            'message': 'User registered successfully',
            'data': {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'tenant_id': user.tenant_id,
                'token': token
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to register user: {str(e)}"
        }), 500

@auth_api.route('/user', methods=['GET'])
def get_current_user():
    """Get current user info API endpoint"""
    # Get authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({
            'status': 'error',
            'message': 'Authorization token is missing'
        }), 401
    
    # Extract token
    token = auth_header.split(' ')[1]
    
    # Verify token
    user = User.verify_auth_token(token)
    if not user:
        return jsonify({
            'status': 'error',
            'message': 'Invalid or expired token'
        }), 401
    
    # Get user roles and permissions
    roles = [role.name for role in user.roles]
    permissions = []
    for role in user.roles:
        permissions.extend(role.permissions)
    
    # Remove duplicates
    permissions = list(set(permissions))
    
    return jsonify({
        'status': 'success',
        'data': {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'tenant_id': user.tenant_id,
            'is_tenant_admin': user.is_tenant_admin,
            'is_system_admin': user.is_system_admin,
            'roles': roles,
            'permissions': permissions
        }
    })

@auth_api.route('/users', methods=['GET'])
def list_users():
    """List users API endpoint"""
    # Get authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({
            'status': 'error',
            'message': 'Authorization token is missing'
        }), 401
    
    # Extract token
    token = auth_header.split(' ')[1]
    
    # Verify token
    current_user = User.verify_auth_token(token)
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'Invalid or expired token'
        }), 401
    
    # Check permission
    if not current_user.has_permission('view_users') and not current_user.is_tenant_admin and not current_user.is_system_admin:
        return jsonify({
            'status': 'error',
            'message': 'You do not have permission to view users'
        }), 403
    
    # Get query parameters
    tenant_id = request.args.get('tenant_id', type=int)
    
    # Build query
    query = User.query
    
    # Filter by tenant if not system admin
    if not current_user.is_system_admin:
        query = query.filter_by(tenant_id=current_user.tenant_id)
    elif tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    
    users = query.all()
    result = []
    
    for user in users:
        roles = [role.name for role in user.roles]
        result.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'tenant_id': user.tenant_id,
            'is_active': user.is_active,
            'is_tenant_admin': user.is_tenant_admin,
            'is_system_admin': user.is_system_admin,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'roles': roles
        })
    
    return jsonify({
        'status': 'success',
        'data': result
    })

@auth_api.route('/roles', methods=['GET'])
def list_roles():
    """List roles API endpoint"""
    # Get authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({
            'status': 'error',
            'message': 'Authorization token is missing'
        }), 401
    
    # Extract token
    token = auth_header.split(' ')[1]
    
    # Verify token
    current_user = User.verify_auth_token(token)
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'Invalid or expired token'
        }), 401
    
    # Check permission
    if not current_user.has_permission('view_roles') and not current_user.is_tenant_admin and not current_user.is_system_admin:
        return jsonify({
            'status': 'error',
            'message': 'You do not have permission to view roles'
        }), 403
    
    # Get query parameters
    tenant_id = request.args.get('tenant_id', type=int)
    include_system_roles = request.args.get('include_system_roles', 'true').lower() == 'true'
    
    # Build query
    query = Role.query
    
    # Filter by tenant if not system admin
    if not current_user.is_system_admin:
        if include_system_roles:
            query = query.filter((Role.tenant_id == current_user.tenant_id) | (Role.is_system_role == True))
        else:
            query = query.filter_by(tenant_id=current_user.tenant_id)
    elif tenant_id:
        if include_system_roles:
            query = query.filter((Role.tenant_id == tenant_id) | (Role.is_system_role == True))
        else:
            query = query.filter_by(tenant_id=tenant_id)
    
    roles = query.all()
    result = []
    
    for role in roles:
        result.append({
            'id': role.id,
            'name': role.name,
            'description': role.description,
            'permissions': role.permissions,
            'tenant_id': role.tenant_id,
            'is_system_role': role.is_system_role
        })
    
    return jsonify({
        'status': 'success',
        'data': result
    })

@auth_api.route('/permissions', methods=['GET'])
def list_permissions():
    """List all available permissions"""
    from app.auth.permission import Permission
    
    # Get authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({
            'status': 'error',
            'message': 'Authorization token is missing'
        }), 401
    
    # Extract token
    token = auth_header.split(' ')[1]
    
    # Verify token
    current_user = User.verify_auth_token(token)
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'Invalid or expired token'
        }), 401
    
    # Only admins can view all permissions
    if not current_user.is_tenant_admin and not current_user.is_system_admin:
        return jsonify({
            'status': 'error',
            'message': 'You do not have permission to view permissions'
        }), 403
    
    permission_groups = Permission.get_permission_groups()
    
    return jsonify({
        'status': 'success',
        'data': permission_groups
    })