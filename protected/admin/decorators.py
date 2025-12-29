# protected/admin/decorators.py
from __future__ import annotations

from functools import wraps
from flask import session, redirect, url_for, request


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("is_admin") is True:
            return fn(*args, **kwargs)
        # niet admin -> naar admin login, met next
        return redirect(url_for("admin.admin_login", next=request.path))
    return wrapper
