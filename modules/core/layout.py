# modules/core/layout.py
from __future__ import annotations

from flask import session


def inject_globals(app):
    """
    Injecteer globale template variabelen:
    - current_user (name, role, is_admin)
    - is_logged_in
    - active_tab komt per template/route mee
    """

    @app.context_processor
    def _inject():
        role = session.get("role")
        return {
            "is_logged_in": bool(session.get("user")),
            "current_user": {
                "name": session.get("user"),
                "role": role,
                "is_admin": bool(session.get("is_admin", False)),
            },
        }
