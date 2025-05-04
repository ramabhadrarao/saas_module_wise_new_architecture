from flask import render_template, jsonify, request

def register_handlers(app):
    """Register error handlers with the Flask app"""
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors"""
        if request_wants_json():
            return jsonify({
                'status': 'error',
                'message': 'Bad request',
                'code': 400
            }), 400
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors"""
        if request_wants_json():
            return jsonify({
                'status': 'error',
                'message': 'Resource not found',
                'code': 404
            }), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        app.logger.error(f'Server Error: {error}')
        if request_wants_json():
            return jsonify({
                'status': 'error',
                'message': 'Internal server error',
                'code': 500
            }), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors"""
        if request_wants_json():
            return jsonify({
                'status': 'error',
                'message': 'Access forbidden',
                'code': 403
            }), 403
        return render_template('errors/403.html'), 403
    
    def request_wants_json():
        """Check if the request is expecting JSON"""
        best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
        return (best == 'application/json' or 
                request.path.startswith('/api/') or
                'application/json' in request.headers.get('Accept', ''))

    # Register custom exception handlers
    class ApiError(Exception):
        """Base exception for API errors"""
        def __init__(self, message, status_code=400, payload=None):
            self.message = message
            self.status_code = status_code
            self.payload = payload
            super().__init__(self.message)
        
        def to_dict(self):
            rv = dict(self.payload or ())
            rv['status'] = 'error'
            rv['message'] = self.message
            rv['code'] = self.status_code
            return rv
    
    @app.errorhandler(ApiError)
    def handle_api_error(error):
        """Handle custom API errors"""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response