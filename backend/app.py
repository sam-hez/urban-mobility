from flask import Flask, jsonify

from routes.system import system
from settings import HOST, PORT


def create_app():
    app = Flask(__name__)
    app.register_blueprint(system)

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


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)
