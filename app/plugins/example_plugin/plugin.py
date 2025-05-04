"""Example plugin implementation"""
from flask import Blueprint, render_template, jsonify, request

class ExamplePlugin:
    """Example plugin class"""
    
    def __init__(self, config=None):
        """Initialize the plugin with configuration"""
        self.config = config or {}
        self.blueprint = self._create_blueprint()
    
    def _create_blueprint(self):
        """Create a Flask blueprint for the plugin"""
        bp = Blueprint(
            'example_plugin',
            __name__,
            template_folder='templates',
            static_folder='static',
            url_prefix='/plugins/example'
        )
        
        @bp.route('/')
        def index():
            """Plugin dashboard"""
            return render_template('example_plugin/dashboard.html', config=self.config)
        
        @bp.route('/api/data')
        def get_data():
            """Sample API endpoint"""
            return jsonify({
                'status': 'success',
                'data': {
                    'message': 'Hello from example plugin!',
                    'config': self.config
                }
            })
        
        return bp
    
    def get_blueprint(self):
        """Get the plugin's blueprint"""
        return self.blueprint
    
    def get_menu_items(self):
        """Get menu items for the sidebar"""
        return [
            {
                'name': 'Example Plugin',
                'url': '/plugins/example',
                'icon': 'puzzle',
                'permission': 'view_plugins'
            }
        ]