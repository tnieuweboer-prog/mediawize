from functools import wraps
from flask import session, redirect, url_for, request

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("is_admin") is True:
            return view(*args, **kwargs)
        return redirect(url_for("admin.admin_login", next=request.path))
    return wrapped

