"""Example plugin for multi-tenant SaaS platform"""

def setup():
    """Setup function called during plugin discovery"""
    return {
        'name': 'Example Plugin',
        'slug': 'example-plugin',
        'version': '1.0.0',
        'description': 'A simple example plugin to demonstrate the plugin system',
        'author': 'Your Name',
        'homepage': 'https://example.com',
        'entry_point': 'example_plugin.plugin:ExamplePlugin',
        'config_schema': {
            'type': 'object',
            'properties': {
                'setting1': {
                    'type': 'string',
                    'title': 'Setting 1',
                    'description': 'A sample setting'
                },
                'setting2': {
                    'type': 'boolean',
                    'title': 'Setting 2',
                    'description': 'Another sample setting'
                }
            }
        },
        'is_system': False,
        'enabled_for_all': False
    }