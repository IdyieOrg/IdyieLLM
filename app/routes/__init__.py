from .llm_routes import llm_bp
from .ping_routes import ping_bp


def register_routes(app):
    app.register_blueprint(llm_bp)
    app.register_blueprint(ping_bp)