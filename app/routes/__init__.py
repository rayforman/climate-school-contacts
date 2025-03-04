# Import blueprints
from app.routes.auth import auth_bp
from app.routes.guests import guests_bp
from app.routes.events import events_bp
from app.routes.reports import reports_bp

# Register main routes
def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(guests_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(reports_bp)