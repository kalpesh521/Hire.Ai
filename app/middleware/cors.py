# cors.py

class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set the Access-Control-Allow-Origin header
        response = self.get_response(request)
        # response['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        # You can set '*' to allow requests from any origin
        response['Access-Control-Allow-Origin'] = '*'
        return response
