"""Task Tracker plugin implementation"""
from flask import Blueprint, render_template, jsonify, request, g
from flask_login import current_user, login_required
from app import db
from app.tenant.middleware import tenant_required, get_current_tenant
from app.auth.rbac import permission_required
from datetime import datetime
import uuid
import json
import os

class Task(db.Model):
    """Task model for the task tracker plugin"""
    __tablename__ = 'plugin_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending')
    priority = db.Column(db.String(50), default='medium')
    due_date = db.Column(db.DateTime, nullable=True)
    
    # User and tenant relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('tasks', lazy='dynamic'))
    tenant = db.relationship('Tenant', backref=db.backref('tasks', lazy='dynamic'))

class TaskTrackerPlugin:
    """Task Tracker plugin class"""
    
    def __init__(self, config=None):
        """Initialize the plugin with configuration"""
        self.config = config or {}
        self.blueprint = self._create_blueprint()
        
        # Create tables if they don't exist
        with db.app.app_context():
            db.create_all()
    
    def _create_blueprint(self):
        """Create a Flask blueprint for the plugin"""
        bp = Blueprint(
            'task_tracker',
            __name__,
            template_folder='templates',
            static_folder='static',
            url_prefix='/plugins/task-tracker'
        )
        
        @bp.route('/')
        @login_required
        @tenant_required
        @permission_required('view_plugins')
        def index():
            """Plugin dashboard"""
            tenant = get_current_tenant()
            return render_template('task_tracker/dashboard.html', 
                                  config=self.config,
                                  tenant=tenant)
        
        @bp.route('/tasks', methods=['GET'])
        @login_required
        @tenant_required
        @permission_required('view_plugins')
        def get_tasks():
            """Get all tasks for the current user and tenant"""
            tenant = get_current_tenant()
            tasks = Task.query.filter_by(
                user_id=current_user.id,
                tenant_id=tenant.id
            ).order_by(Task.created_at.desc()).all()
            
            task_list = []
            for task in tasks:
                task_list.append({
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'priority': task.priority,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'created_at': task.created_at.isoformat(),
                    'updated_at': task.updated_at.isoformat()
                })
            
            return jsonify({
                'status': 'success',
                'data': task_list
            })
        
        @bp.route('/tasks', methods=['POST'])
        @login_required
        @tenant_required
        @permission_required('view_plugins')
        def create_task():
            """Create a new task"""
            tenant = get_current_tenant()
            data = request.json
            
            # Check if max tasks limit is reached
            max_tasks = self.config.get('max_tasks', 100)
            current_task_count = Task.query.filter_by(
                tenant_id=tenant.id
            ).count()
            
            if current_task_count >= max_tasks:
                return jsonify({
                    'status': 'error',
                    'message': f'Maximum task limit ({max_tasks}) reached'
                }), 400
            
            # Get default priority from config
            default_priority = self.config.get('default_priority', 'medium')
            
            # Create new task
            task = Task(
                title=data.get('title'),
                description=data.get('description'),
                status='pending',
                priority=data.get('priority', default_priority),
                user_id=current_user.id,
                tenant_id=tenant.id
            )
            
            # Add due date if enabled and provided
            if self.config.get('enable_due_dates', True) and data.get('due_date'):
                try:
                    task.due_date = datetime.fromisoformat(data.get('due_date'))
                except ValueError:
                    pass
            
            db.session.add(task)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Task created successfully',
                'data': {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'priority': task.priority,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'created_at': task.created_at.isoformat(),
                    'updated_at': task.updated_at.isoformat()
                }
            })
        
        @bp.route('/tasks/<int:task_id>', methods=['PUT'])
        @login_required
        @tenant_required
        @permission_required('view_plugins')
        def update_task(task_id):
            """Update a task"""
            tenant = get_current_tenant()
            data = request.json
            
            # Find the task
            task = Task.query.filter_by(
                id=task_id,
                user_id=current_user.id,
                tenant_id=tenant.id
            ).first()
            
            if not task:
                return jsonify({
                    'status': 'error',
                    'message': 'Task not found'
                }), 404
            
            # Update task fields
            if 'title' in data:
                task.title = data['title']
            
            if 'description' in data:
                task.description = data['description']
            
            if 'status' in data:
                task.status = data['status']
            
            if 'priority' in data:
                task.priority = data['priority']
            
            # Update due date if enabled
            if self.config.get('enable_due_dates', True) and 'due_date' in data:
                if data['due_date']:
                    try:
                        task.due_date = datetime.fromisoformat(data['due_date'])
                    except ValueError:
                        pass
                else:
                    task.due_date = None
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Task updated successfully',
                'data': {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'priority': task.priority,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'created_at': task.created_at.isoformat(),
                    'updated_at': task.updated_at.isoformat()
                }
            })
        
        @bp.route('/tasks/<int:task_id>', methods=['DELETE'])
        @login_required
        @tenant_required
        @permission_required('view_plugins')
        def delete_task(task_id):
            """Delete a task"""
            tenant = get_current_tenant()
            
            # Find the task
            task = Task.query.filter_by(
                id=task_id,
                user_id=current_user.id,
                tenant_id=tenant.id
            ).first()
            
            if not task:
                return jsonify({
                    'status': 'error',
                    'message': 'Task not found'
                }), 404
            
            # Delete the task
            db.session.delete(task)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Task deleted successfully'
            })
        
        return bp
    
    def get_blueprint(self):
        """Get the plugin's blueprint"""
        return self.blueprint
    
    def get_menu_items(self):
        """Get menu items for the sidebar"""
        return [
            {
                'name': 'Task Tracker',
                'url': '/plugins/task-tracker',
                'icon': 'check-square',
                'permission': 'view_plugins'
            }
        ]