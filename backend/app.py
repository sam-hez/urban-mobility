import os
import threading

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from api_routes import api
from routes.system import system
from settings import HOST, PORT
from validation import ApiError

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

FRONTEND_DIR = os.path.join(
    BASE_DIR,
    "frontend"
)


def create_app():
    
    app = Flask(
        __name__,
        static_folder=FRONTEND_DIR,
        static_url_path=""
    )

    CORS(app)                       
    app.json.sort_keys = False      
    app.register_blueprint(api)
    app.register_blueprint(system)

    @app.route("/")
    def frontend():

        return send_from_directory(
            FRONTEND_DIR,
            "index.html"
        )

    @app.errorhandler(ApiError)
    def handle_api_error(error):
        body = {"error": error.message}
        if error.field:
            body["field"] = error.field
        return jsonify(body), error.status


    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        app.logger.error("Database error: %s", error)
        return jsonify({"error": "The database is unavailable or the query failed. Try again."}), 503


    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.description}), error.code


    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unexpected error")
        return jsonify({"error": "Internal server error"}), 500


    return app

app = create_app()


def warm_cache():
    client = app.test_client()
    for url in ["/api/filters", "/api/zones", "/api/summary", "/api/charts/hourly",
                "/api/charts/daily", "/api/charts/boroughs", "/api/charts/top-zones",
                "/api/charts/payment-types", "/api/charts/distance-distribution", "/api/trips"]:
        try:
            client.get(url)
        except Exception:
            pass   

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=warm_cache, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False)
