"""Notes plugin implementation"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, g, abort
from flask_login import current_user, login_required
from app.auth.rbac import permission_required
from app.tenant.middleware import tenant_required, get_current_tenant
from app import db
import os
import logging
from datetime import datetime
from .models import Note
from .forms import NoteForm

logger = logging.getLogger(__name__)

class NotesPlugin:
    """Notes plugin class"""
    
    def __init__(self, config=None):
        """Initialize the plugin with configuration"""
        self.config = config or {}
        self.blueprint = self._create_blueprint()
        
        # Get configuration values with defaults
        self.max_notes_per_user = self.config.get('max_notes_per_user', 100)
        self.enable_sharing = self.config.get('enable_sharing', True)
        self.enable_categories = self.config.get('enable_categories', True)
    
    def _create_blueprint(self):
        """Create a Flask blueprint for the plugin"""
        # The static_folder and template_folder are relative to the plugin directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        bp = Blueprint(
            'notes_plugin',
            __name__,
            template_folder='templates',
            static_folder='static',
            url_prefix='/plugins/notes'
        )
        
        @bp.route('/')
        # @login_required
        # @tenant_required
        def index():
            """Notes dashboard"""
            # Get the current tenant and user
            tenant = get_current_tenant()
            category = request.args.get('category')
            include_archived = request.args.get('archived', 'false') == 'true'
            
            if category:
                notes = Note.get_notes_by_category(current_user.id, category, include_archived)
            else:
                notes = Note.get_notes_for_user(current_user.id, include_archived)
            
            # Get all distinct categories for the filter
            categories = db.session.query(Note.category).filter(
                Note.user_id == current_user.id,
                Note.category != None,
                Note.category != ''
            ).distinct().all()
            
            categories = [c[0] for c in categories]
            
            return render_template(
                'notes_plugin/index.html', 
                notes=notes, 
                categories=categories,
                current_category=category,
                include_archived=include_archived,
                enable_categories=self.enable_categories
            )
        
        @bp.route('/create', methods=['GET', 'POST'])
        # @login_required
        # @tenant_required
        def create():
            """Create a new note"""
            tenant = get_current_tenant()
            form = NoteForm()
            
            # Check if user has reached the limit
            user_notes_count = Note.query.filter_by(
                user_id=current_user.id,
                tenant_id=tenant.id
            ).count()
            
            if user_notes_count >= self.max_notes_per_user:
                flash(f'You have reached the maximum limit of {self.max_notes_per_user} notes.', 'warning')
                return redirect(url_for('notes_plugin.index'))
            
            if form.validate_on_submit():
                # Hide category field if categories are disabled
                category = form.category.data if self.enable_categories else None
                
                note = Note.create_note(
                    tenant_id=tenant.id,
                    user_id=current_user.id,
                    title=form.title.data,
                    content=form.content.data,
                    category=category
                )
                
                if form.is_pinned.data:
                    note.is_pinned = True
                    db.session.commit()
                
                flash('Note created successfully!', 'success')
                return redirect(url_for('notes_plugin.index'))
            
            return render_template(
                'notes_plugin/create.html', 
                form=form,
                enable_categories=self.enable_categories
            )
        
        @bp.route('/<int:note_id>', methods=['GET'])
        # @login_required
        # @tenant_required
        def view(note_id):
            """View a note"""
            tenant = get_current_tenant()
            note = Note.query.get_or_404(note_id)
            
            # Check if user owns the note or has access
            if note.user_id != current_user.id and not self.enable_sharing:
                abort(403)
            
            # Check if note belongs to the current tenant
            if note.tenant_id != tenant.id:
                abort(404)
            
            return render_template('notes_plugin/view.html', note=note)
        
        @bp.route('/<int:note_id>/edit', methods=['GET', 'POST'])
        # @login_required
        # @tenant_required
        def edit(note_id):
            """Edit a note"""
            tenant = get_current_tenant()
            note = Note.query.get_or_404(note_id)
            
            # Check if user owns the note
            if note.user_id != current_user.id:
                abort(403)
            
            # Check if note belongs to the current tenant
            if note.tenant_id != tenant.id:
                abort(404)
            
            form = NoteForm(obj=note)
            
            if form.validate_on_submit():
                form.populate_obj(note)
                
                # Hide category field if categories are disabled
                if not self.enable_categories:
                    note.category = None
                
                db.session.commit()
                flash('Note updated successfully!', 'success')
                return redirect(url_for('notes_plugin.index'))
            
            return render_template(
                'notes_plugin/edit.html', 
                form=form, 
                note=note,
                enable_categories=self.enable_categories
            )
        
        @bp.route('/<int:note_id>/pin', methods=['POST'])
        # @login_required
        # @tenant_required
        def toggle_pin(note_id):
            """Toggle pin status of a note"""
            tenant = get_current_tenant()
            note = Note.query.get_or_404(note_id)
            
            # Check if user owns the note
            if note.user_id != current_user.id:
                abort(403)
            
            # Check if note belongs to the current tenant
            if note.tenant_id != tenant.id:
                abort(404)
            
            note.is_pinned = not note.is_pinned
            db.session.commit()
            
            flash(f'Note {"pinned" if note.is_pinned else "unpinned"}!', 'success')
            return redirect(url_for('notes_plugin.index'))
        
        @bp.route('/<int:note_id>/archive', methods=['POST'])
        # @login_required
        # @tenant_required
        def toggle_archive(note_id):
            """Toggle archive status of a note"""
            tenant = get_current_tenant()
            note = Note.query.get_or_404(note_id)
            
            # Check if user owns the note
            if note.user_id != current_user.id:
                abort(403)
            
            # Check if note belongs to the current tenant
            if note.tenant_id != tenant.id:
                abort(404)
            
            note.is_archived = not note.is_archived
            db.session.commit()
            
            flash(f'Note {"archived" if note.is_archived else "restored"}!', 'success')
            return redirect(url_for('notes_plugin.index'))
        
        @bp.route('/<int:note_id>/delete', methods=['POST'])
        # @login_required
        # @tenant_required
        def delete(note_id):
            """Delete a note"""
            tenant = get_current_tenant()
            note = Note.query.get_or_404(note_id)
            
            # Check if user owns the note
            if note.user_id != current_user.id:
                abort(403)
            
            # Check if note belongs to the current tenant
            if note.tenant_id != tenant.id:
                abort(404)
            
            db.session.delete(note)
            db.session.commit()
            
            flash('Note deleted successfully!', 'success')
            return redirect(url_for('notes_plugin.index'))
        
        return bp
    
    def get_blueprint(self):
        """Get the plugin's blueprint"""
        return self.blueprint
    
    def get_menu_items(self):
        """Get menu items for the sidebar"""
        return [
            {
                'name': 'Notes',
                'url': '/plugins/notes',
                'icon': 'note',
                'permission': None  # No specific permission required
            }
        ]

    def install(self, tenant_id=None):
        """Custom install hook - create database tables"""
        # This would create the necessary tables for the plugin
        # In a real-world scenario, you'd use migrations
        try:
            from app import db
            from .models import Note
            
            # Create tables if they don't exist
            # This is simplified; in production, use Flask-Migrate
            db.create_all()
            logger.info("Notes plugin installed successfully")
            return True
        except Exception as e:
            logger.error(f"Error installing Notes plugin: {str(e)}")
            return False
    
    def uninstall(self, tenant_id=None):
        """Custom uninstall hook - clean up resources"""
        # This would clean up any resources created by the plugin
        try:
            # In a real implementation, you might want to ask
            # if the tenant wants to keep their data
            if tenant_id:
                from .models import Note
                Note.query.filter_by(tenant_id=tenant_id).delete()
                db.session.commit()
            
            logger.info("Notes plugin uninstalled successfully")
            return True
        except Exception as e:
            logger.error(f"Error uninstalling Notes plugin: {str(e)}")
            return False