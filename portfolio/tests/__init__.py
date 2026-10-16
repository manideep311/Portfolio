import logging

# Expected 403/404 responses in tests would otherwise print full tracebacks.
logging.getLogger("django.request").setLevel(logging.ERROR)
logging.getLogger("django.security").setLevel(logging.ERROR)
