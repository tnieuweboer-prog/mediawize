# protected/admin/__init__.py
from flask import Blueprint

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="../../templates/admin",
    static_folder="../../static/admin",
)

from . import routes  # noqa: E402,F401
