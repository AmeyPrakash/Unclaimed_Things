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

class SecurityHeadersMiddleware:
    """
    Injects Content-Security-Policy (CSP) and defense-in-depth security headers per TRD Section 9.
    Works reliably across development, testing, and production deployment environments.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # 1. Content Security Policy (TRD Section 9)
        csp_directives = [
            "default-src 'self'",
            "img-src 'self' data: blob: http: https:",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000 http://localhost:5173 http://127.0.0.1:5173 https://integrate.api.nvidia.com",
            "font-src 'self'",
            "object-src 'none'",
            "frame-ancestors 'none'"
        ]
        response['Content-Security-Policy'] = "; ".join(csp_directives)

        # 2. Permissions Policy (Disables browser hardware access by default)
        response['Permissions-Policy'] = "camera=(), microphone=(), geolocation=()"

        # 3. MIME sniffing and clickjacking defense
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response

