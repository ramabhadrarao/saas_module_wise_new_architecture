"""Notes plugin for multi-tenant SaaS platform"""

def setup():
    """Setup function called during plugin discovery"""
    return {
        'name': 'Notes',
        'slug': 'notes',
        'version': '1.0.0',
        'description': 'A simple notes management plugin for organizing text notes',
        'author': 'Your Name',
        'homepage': 'https://example.com',
        'entry_point': 'notes_plugin.plugin:NotesPlugin',
        'config_schema': {
            'type': 'object',
            'properties': {
                'max_notes_per_user': {
                    'type': 'integer',
                    'title': 'Max Notes Per User',
                    'description': 'Maximum number of notes a user can create',
                    'default': 100
                },
                'enable_sharing': {
                    'type': 'boolean',
                    'title': 'Enable Note Sharing',
                    'description': 'Allow users to share notes with others in the tenant',
                    'default': True
                },
                'enable_categories': {
                    'type': 'boolean',
                    'title': 'Enable Categories',
                    'description': 'Allow users to categorize notes',
                    'default': True
                }
            }
        },
        'is_system': False,
        'enabled_for_all': False
    }