"""
Con5013 Utility Functions
Helper functions for the Con5013 extension.
"""

from flask import current_app

def get_con5013_instance():
    """Get the Con5013 instance from the current Flask app."""
    if not hasattr(current_app, 'extensions'):
        raise RuntimeError("Con5013 not initialized with this Flask app")
    
    con5013 = current_app.extensions.get('con5013')
    if not con5013:
        raise RuntimeError("Con5013 not found in Flask app extensions")
    
    return con5013

