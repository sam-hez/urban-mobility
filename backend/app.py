from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from routes import api
from validation import ApiError

app = Flask(__name__)
CORS(app)                      
app.json.sort_keys = False     
app.register_blueprint(api)


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


if __name__ == "__main__":
    app.run(debug=True)