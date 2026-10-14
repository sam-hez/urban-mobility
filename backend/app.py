from flask import Flask, jsonify

from routes.system import system
from settings import HOST, PORT

import os
import threading


from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from routes import api
from validation import ApiError


def create_app():
    app = Flask(__name__)
    CORS(app)                       
    app.json.sort_keys = False      
    app.register_blueprint(api)

    @app.after_request
    def add_cors_header(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "server error"}), 500

    return app


app = create_app()



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
