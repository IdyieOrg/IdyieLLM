from .ping_routes import ping_bp


def register_routes(app):
    app.register_blueprint(ping_bp)
