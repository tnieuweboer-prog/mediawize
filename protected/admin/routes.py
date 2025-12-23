# protected/admin/routes.py
from flask import render_template
from . import admin_bp

# ---------------------------------------------------------
# ROUTE MAP (admin)
# ---------------------------------------------------------
# GET  /admin                          -> Admin dashboard (overzicht)
# GET  /admin/schools                   -> Scholen lijst
# GET  /admin/schools/new               -> Nieuwe school formulier
# POST /admin/schools/new               -> School aanmaken
# GET  /admin/schools/<id>              -> School details (tabs: gegevens/branding/inrichting/tools)
# POST /admin/schools/<id>/save         -> School opslaan
#
# GET  /admin/teachers                  -> Docenten lijst
# GET  /admin/teachers/new              -> Nieuwe docent formulier
# POST /admin/teachers/new              -> Docent aanmaken
# GET  /admin/teachers/<id>             -> Docent details + tool overrides
# POST /admin/teachers/<id>/save        -> Docent opslaan
#
# GET  /admin/tools                     -> Tools catalogus
# GET  /admin/tools/<key>               -> Tool detail (status/omschrijving)
# POST /admin/tools/<key>/save          -> Tool opslaan
#
# (optioneel later)
# GET  /admin/system                    -> Logs/versie/maintenance
# ---------------------------------------------------------


@admin_bp.get("/")
def admin_dashboard():
    # Stap 1: alleen bevestigen dat admin blueprint werkt
    return render_template("dashboard.html")

