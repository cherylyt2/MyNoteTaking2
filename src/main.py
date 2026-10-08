import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from sqlalchemy.engine import make_url

from src.models.user import db
from src.routes.folder import folder_bp
from src.routes.note import note_bp
from src.routes.user import user_bp


def create_app(config=None):
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-only-change-me'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping': True},
    )
    if config:
        app.config.update(config)

    database_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    if database_url:
        url = make_url(database_url)
        if url.drivername in ('postgres', 'postgresql'):
            app.config['SQLALCHEMY_DATABASE_URI'] = url.set(
                drivername='postgresql+psycopg'
            )
            app.config['SQLALCHEMY_ENGINE_OPTIONS'].update({
                'pool_size': 1,
                'max_overflow': 0,
            })

    CORS(app)
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(note_bp, url_prefix='/api')
    app.register_blueprint(folder_bp, url_prefix='/api')

    db.init_app(app)
    if database_url:
        with app.app_context():
            db.create_all()

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)

        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        return "index.html not found", 404

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)