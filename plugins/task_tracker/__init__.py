"""Task Tracker plugin for multi-tenant SaaS platform"""

def setup():
    """Setup function called during plugin discovery"""
    return {
        'name': 'Task Tracker',
        'slug': 'task-tracker',
        'version': '1.0.0',
        'description': 'A simple task tracker plugin for managing to-do items',
        'author': 'Your Name',
        'homepage': 'https://example.com',
        'entry_point': 'task_tracker.plugin:TaskTrackerPlugin',
        'config_schema': {
            'type': 'object',
            'properties': {
                'default_priority': {
                    'type': 'string',
                    'title': 'Default Priority',
                    'description': 'The default priority for new tasks',
                    'enum': ['low', 'medium', 'high'],
                    'default': 'medium'
                },
                'enable_due_dates': {
                    'type': 'boolean',
                    'title': 'Enable Due Dates',
                    'description': 'Whether to enable due dates for tasks',
                    'default': True
                },
                'max_tasks': {
                    'type': 'integer',
                    'title': 'Maximum Tasks',
                    'description': 'Maximum number of tasks allowed',
                    'minimum': 10,
                    'default': 100
                }
            }
        },
        'is_system': False,
        'enabled_for_all': True
    }