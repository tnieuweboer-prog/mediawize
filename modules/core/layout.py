# modules/core/layout.py
from flask import session

def inject_globals(app):
    @app.context_processor
    def _inject():
        return {
            "current_user": {
                "name": session.get("user"),
                "role": session.get("role"),
                "is_admin": session.get("is_admin", False),
            }
        }

