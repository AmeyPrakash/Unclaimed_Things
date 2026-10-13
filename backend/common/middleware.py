import uuid

class RequestIdMiddleware:
    """
    Ensures every request has a unique request_id.
    Reads X-Request-ID if provided by client or reverse proxy, else generates a UUID.
    Attaches X-Request-ID to the HTTP response.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request.request_id = request_id
        
        response = self.get_response(request)
        response['X-Request-ID'] = request_id
        return response
