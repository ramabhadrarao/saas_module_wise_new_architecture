"""Frontend routes for authentication and authorization"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.auth.user import User, Role
from app.auth.decorators import active_required
from app.auth.rbac import permission_required, role_required
from app.tenant.tenant import Tenant
import logging

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me', 'false') == 'true'
        
        # Validate required fields
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('auth/login.html', title='Login')
        
        # Find user by username or email
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if user is None or not user.verify_password(password):
            flash('Invalid username or password', 'danger')
            return render_template('auth/login.html', title='Login')
        
        if not user.is_active:
            flash('This account is inactive. Please contact support.', 'warning')
            return render_template('auth/login.html', title='Login')
        
        # Check tenant status if user belongs to a tenant
        if user.tenant_id:
            tenant = Tenant.query.get(user.tenant_id)
            if tenant and tenant.status != 'active':
                flash(f"Your tenant '{tenant.name}' is {tenant.status}", 'warning')
                return render_template('auth/login.html', title='Login')
        
        # Log in user
        login_user(user, remember=remember_me)
        
        # Update last login time
        user.update_last_login()
        
        # Redirect to next page if specified, otherwise to home
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        
        return redirect(url_for('main.index'))
    
    return render_template('auth/login.html', title='Login')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Get tenant if specified
    tenant_slug = request.args.get('tenant')
    tenant = None
    if tenant_slug:
        tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if tenant and tenant.status != 'active':
            flash(f"Tenant '{tenant.name}' is currently {tenant.status}", 'warning')
            return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        tenant_id = request.form.get('tenant_id')
        
        # Validate required fields
        if not username or not email or not password or not confirm_password:
            flash('All fields are required', 'danger')
            return render_template('auth/register.html', title='Register', tenant=tenant)
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/register.html', title='Register', tenant=tenant)
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash(f"Username '{username}' is already taken", 'danger')
            return render_template('auth/register.html', title='Register', tenant=tenant)
        
        if User.query.filter_by(email=email).first():
            flash(f"Email '{email}' is already registered", 'danger')
            return render_template('auth/register.html', title='Register', tenant=tenant)
        
        try:
            # Create new user
            user = User.create_user(
                email=email,
                username=username,
                password=password,
                tenant_id=tenant.id if tenant else None,
                first_name=first_name,
                last_name=last_name
            )
            
            # Add default user role
            user_role = Role.query.filter_by(name='User').first()
            if user_role:
                user.roles.append(user_role)
                db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            flash(f"Failed to register user: {str(e)}", 'danger')
    
    return render_template('auth/register.html', title='Register', tenant=tenant)

@auth_bp.route('/profile')
@login_required
@active_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', title='My Profile')

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@active_required
def edit_profile():
    """Edit user profile page"""
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        try:
            # Update user profile
            current_user.first_name = first_name
            current_user.last_name = last_name
            db.session.commit()
            
            flash('Profile updated successfully', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            flash(f"Failed to update profile: {str(e)}", 'danger')
    
    return render_template('auth/edit_profile.html', title='Edit Profile')

@auth_bp.route('/password/change', methods=['GET', 'POST'])
@login_required
@active_required
def change_password():
    """Change password page"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required', 'danger')
            return render_template('auth/change_password.html', title='Change Password')
        
        # Check if current password is correct
        if not current_user.verify_password(current_password):
            flash('Current password is incorrect', 'danger')
            return render_template('auth/change_password.html', title='Change Password')
        
        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return render_template('auth/change_password.html', title='Change Password')
        
        try:
            # Update password
            current_user.password = new_password
            db.session.commit()
            
            flash('Password changed successfully', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            flash(f"Failed to change password: {str(e)}", 'danger')
    
    return render_template('auth/change_password.html', title='Change Password')

# Admin routes
@auth_bp.route('/users')
@login_required
@active_required
@permission_required('view_users')
def users():
    """User management page"""
    # Get all users
    if current_user.is_system_admin:
        users = User.query.all()
    else:
        # Tenant admins can only see users in their own tenant
        users = User.query.filter_by(tenant_id=current_user.tenant_id).all()
    
    return render_template('auth/users.html', title='User Management', users=users)

@auth_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@active_required
@permission_required('create_user')
def create_user():
    """Create user page"""
    # Get available roles
    if current_user.is_system_admin:
        roles = Role.query.all()
        tenants = Tenant.query.all()
    else:
        # Tenant admins can only assign roles in their own tenant
        roles = Role.query.filter((Role.tenant_id == current_user.tenant_id) | (Role.is_system_role == True)).all()
        tenants = Tenant.query.filter_by(id=current_user.tenant_id).all()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        tenant_id = request.form.get('tenant_id')
        is_tenant_admin = request.form.get('is_tenant_admin') == 'on'
        is_system_admin = request.form.get('is_system_admin') == 'on'
        role_ids = request.form.getlist('roles')
        
        # Validate required fields
        if not username or not email or not password or not confirm_password:
            flash('Username, email, and password are required', 'danger')
            return render_template('auth/create_user.html', title='Create User', 
                                 roles=roles, tenants=tenants)
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/create_user.html', title='Create User', 
                                 roles=roles, tenants=tenants)
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash(f"Username '{username}' is already taken", 'danger')
            return render_template('auth/create_user.html', title='Create User', 
                                 roles=roles, tenants=tenants)
        
        if User.query.filter_by(email=email).first():
            flash(f"Email '{email}' is already registered", 'danger')
            return render_template('auth/create_user.html', title='Create User', 
                                 roles=roles, tenants=tenants)
        
        # Non-system admins can only create users in their own tenant
        if not current_user.is_system_admin and int(tenant_id) != current_user.tenant_id:
            flash('You can only create users in your own tenant', 'danger')
            return render_template('auth/create_user.html', title='Create User', 
                                 roles=roles, tenants=tenants)
        
        # Non-system admins cannot create system admins
        if not current_user.is_system_admin and is_system_admin:
            flash('You cannot create system administrators', 'danger')
            return render_template('auth/create_user.html', title='Create User', 
                                 roles=roles, tenants=tenants)
        
        try:
            # Create new user
            user = User.create_user(
                email=email,
                username=username,
                password=password,
                tenant_id=tenant_id,
                first_name=first_name,
                last_name=last_name,
                is_tenant_admin=is_tenant_admin,
                is_system_admin=is_system_admin
            )
            
            # Add selected roles
            for role_id in role_ids:
                role = Role.query.get(role_id)
                if role:
                    # Tenant admins can only assign tenant roles or system roles
                    if current_user.is_system_admin or not role.tenant_id or role.tenant_id == current_user.tenant_id:
                        user.roles.append(role)
            
            db.session.commit()
            
            flash(f"User '{username}' created successfully", 'success')
            return redirect(url_for('auth.users'))
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            flash(f"Failed to create user: {str(e)}", 'danger')
    
    return render_template('auth/create_user.html', title='Create User', 
                         roles=roles, tenants=tenants)

@auth_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@active_required
@permission_required('edit_user')
def edit_user(user_id):
    """Edit user page"""
    # Get user
    user = User.query.get_or_404(user_id)
    
    # Check if user has permission to edit this user
    if not current_user.is_system_admin and user.tenant_id != current_user.tenant_id:
        flash('You do not have permission to edit this user', 'danger')
        return redirect(url_for('auth.users'))
    
    # Get available roles
    if current_user.is_system_admin:
        roles = Role.query.all()
        tenants = Tenant.query.all()
    else:
        # Tenant admins can only assign roles in their own tenant
        roles = Role.query.filter((Role.tenant_id == current_user.tenant_id) | (Role.is_system_role == True)).all()
        tenants = Tenant.query.filter_by(id=current_user.tenant_id).all()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        tenant_id = request.form.get('tenant_id')
        is_active = request.form.get('is_active') == 'on'
        is_tenant_admin = request.form.get('is_tenant_admin') == 'on'
        is_system_admin = request.form.get('is_system_admin') == 'on'
        role_ids = request.form.getlist('roles')
        new_password = request.form.get('new_password')
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            flash(f"Username '{username}' is already taken", 'danger')
            return render_template('auth/edit_user.html', title='Edit User', 
                                 user=user, roles=roles, tenants=tenants)
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            flash(f"Email '{email}' is already registered", 'danger')
            return render_template('auth/edit_user.html', title='Edit User', 
                                 user=user, roles=roles, tenants=tenants)
        
        # Non-system admins can only edit users in their own tenant
        if not current_user.is_system_admin and int(tenant_id) != current_user.tenant_id:
            flash('You can only assign users to your own tenant', 'danger')
            return render_template('auth/edit_user.html', title='Edit User', 
                                 user=user, roles=roles, tenants=tenants)
        
        # Non-system admins cannot create system admins
        if not current_user.is_system_admin and is_system_admin:
            flash('You cannot create system administrators', 'danger')
            return render_template('auth/edit_user.html', title='Edit User', 
                                 user=user, roles=roles, tenants=tenants)
        
        try:
            # Update user
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.tenant_id = tenant_id
            user.is_active = is_active
            user.is_tenant_admin = is_tenant_admin
            user.is_system_admin = is_system_admin
            
            # Update password if provided
            if new_password:
                user.password = new_password
            
            # Update roles
            user.roles.clear()
            for role_id in role_ids:
                role = Role.query.get(role_id)
                if role:
                    # Tenant admins can only assign tenant roles or system roles
                    if current_user.is_system_admin or not role.tenant_id or role.tenant_id == current_user.tenant_id:
                        user.roles.append(role)
            
            db.session.commit()
            
            flash(f"User '{username}' updated successfully", 'success')
            return redirect(url_for('auth.users'))
            
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            flash(f"Failed to update user: {str(e)}", 'danger')
    
    return render_template('auth/edit_user.html', title='Edit User', 
                         user=user, roles=roles, tenants=tenants)

@auth_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@active_required
@permission_required('delete_user')
def delete_user(user_id):
    """Delete user"""
    # Get user
    user = User.query.get_or_404(user_id)
    
    # Check if user has permission to delete this user
    if not current_user.is_system_admin and user.tenant_id != current_user.tenant_id:
        flash('You do not have permission to delete this user', 'danger')
        return redirect(url_for('auth.users'))
    
    # Cannot delete yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('auth.users'))
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        flash(f"User '{username}' deleted successfully", 'success')
        return redirect(url_for('auth.users'))
        
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        flash(f"Failed to delete user: {str(e)}", 'danger')
        return redirect(url_for('auth.users'))

# Role management routes
@auth_bp.route('/roles')
@login_required
@active_required
@permission_required('view_roles')
def roles():
    """Role management page"""
    # Get all roles
    if current_user.is_system_admin:
        roles = Role.query.all()
    else:
        # Tenant admins can only see roles in their own tenant and system roles
        roles = Role.query.filter((Role.tenant_id == current_user.tenant_id) | (Role.is_system_role == True)).all()
    
    return render_template('auth/roles.html', title='Role Management', roles=roles)

@auth_bp.route('/roles/create', methods=['GET', 'POST'])
@login_required
@active_required
@permission_required('create_role')
def create_role():
    """Create role page"""
    # Get all permissions
    from app.auth.permission import Permission
    permission_groups = Permission.get_permission_groups()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        permissions = request.form.getlist('permissions')
        is_system_role = request.form.get('is_system_role') == 'on'
        
        # Validate required fields
        if not name:
            flash('Role name is required', 'danger')
            return render_template('auth/create_role.html', title='Create Role', 
                                 permission_groups=permission_groups)
        
        # Check if role name already exists
        if Role.query.filter_by(name=name).first():
            flash(f"Role name '{name}' already exists", 'danger')
            return render_template('auth/create_role.html', title='Create Role', 
                                 permission_groups=permission_groups)
        
        # Non-system admins cannot create system roles
        if not current_user.is_system_admin and is_system_role:
            flash('You cannot create system roles', 'danger')
            return render_template('auth/create_role.html', title='Create Role', 
                                 permission_groups=permission_groups)
        
        try:
            # Create new role
            role = Role(
                name=name,
                description=description,
                permissions=permissions,
                is_system_role=is_system_role,
                tenant_id=None if is_system_role else current_user.tenant_id
            )
            
            db.session.add(role)
            db.session.commit()
            
            flash(f"Role '{name}' created successfully", 'success')
            return redirect(url_for('auth.roles'))
            
        except Exception as e:
            logger.error(f"Error creating role: {str(e)}")
            flash(f"Failed to create role: {str(e)}", 'danger')
    
    return render_template('auth/create_role.html', title='Create Role', 
                         permission_groups=permission_groups)

@auth_bp.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
@active_required
@permission_required('edit_role')
def edit_role(role_id):
    """Edit role page"""
    # Get role
    role = Role.query.get_or_404(role_id)
    
    # Check if user has permission to edit this role
    if not current_user.is_system_admin and role.is_system_role:
        flash('You do not have permission to edit system roles', 'danger')
        return redirect(url_for('auth.roles'))
    
    if not current_user.is_system_admin and role.tenant_id != current_user.tenant_id:
        flash('You do not have permission to edit this role', 'danger')
        return redirect(url_for('auth.roles'))
    
    # Get all permissions
    from app.auth.permission import Permission
    permission_groups = Permission.get_permission_groups()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        permissions = request.form.getlist('permissions')
        
        # Validate required fields
        if not name:
            flash('Role name is required', 'danger')
            return render_template('auth/edit_role.html', title='Edit Role', 
                                 role=role, permission_groups=permission_groups)
        
        # Check if role name already exists
        existing_role = Role.query.filter_by(name=name).first()
        if existing_role and existing_role.id != role.id:
            flash(f"Role name '{name}' already exists", 'danger')
            return render_template('auth/edit_role.html', title='Edit Role', 
                                 role=role, permission_groups=permission_groups)
        
        try:
            # Update role
            role.name = name
            role.description = description
            role.permissions = permissions
            
            db.session.commit()
            
            flash(f"Role '{name}' updated successfully", 'success')
            return redirect(url_for('auth.roles'))
            
        except Exception as e:
            logger.error(f"Error updating role: {str(e)}")
            flash(f"Failed to update role: {str(e)}", 'danger')
    
    return render_template('auth/edit_role.html', title='Edit Role', 
                         role=role, permission_groups=permission_groups)

@auth_bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@active_required
@permission_required('delete_role')
def delete_role(role_id):
    """Delete role"""
    # Get role
    role = Role.query.get_or_404(role_id)
    
    # Check if user has permission to delete this role
    if not current_user.is_system_admin and role.is_system_role:
        flash('You cannot delete system roles', 'danger')
        return redirect(url_for('auth.roles'))
    
    if not current_user.is_system_admin and role.tenant_id != current_user.tenant_id:
        flash('You do not have permission to delete this role', 'danger')
        return redirect(url_for('auth.roles'))
    
    try:
        # Check if role is assigned to any users
        if role.users:
            flash(f"Cannot delete role '{role.name}' because it is assigned to users", 'danger')
            return redirect(url_for('auth.roles'))
        
        role_name = role.name
        db.session.delete(role)
        db.session.commit()
        
        flash(f"Role '{role_name}' deleted successfully", 'success')
        return redirect(url_for('auth.roles'))
        
    except Exception as e:
        logger.error(f"Error deleting role: {str(e)}")
        flash(f"Failed to delete role: {str(e)}", 'danger')
        return redirect(url_for('auth.roles'))