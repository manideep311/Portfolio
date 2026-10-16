import secrets

from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """Adds a nonce-based Content-Security-Policy to public HTML pages.

    The Django admin is left on its defaults so its widgets keep working.
    Templates read the nonce as ``{{ request.csp_nonce }}``.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_prefix = "/" + settings.ADMIN_URL

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)

        if request.path.startswith(self.admin_prefix):
            return response
        if "text/html" not in response.get("Content-Type", ""):
            return response

        img_src = " ".join(["'self'", "data:", *settings.CSP_IMG_ORIGINS])
        policy = "; ".join(
            [
                "default-src 'self'",
                f"script-src 'self' 'nonce-{request.csp_nonce}'",
                "style-src 'self' 'unsafe-inline'",
                f"img-src {img_src}",
                "font-src 'self'",
                "connect-src 'self'",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
            ]
        )
        response.setdefault("Content-Security-Policy", policy)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response
