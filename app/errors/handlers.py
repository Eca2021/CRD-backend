from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error="Bad Request", detail=str(e)), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify(error="Unauthorized", detail=str(e)), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify(error="Forbidden", detail=str(e)), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Not Found"), 404

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify(error="Unprocessable Entity", detail=str(e)), 422

    @app.errorhandler(Exception)
    def internal(e):
        app.logger.exception(e)
        return jsonify(error="Internal Server Error"), 500
