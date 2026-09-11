import json

from django.http import HttpResponse


def htmx_success(toast):
    """Empty 204 response that refreshes the page and raises a toast."""
    response = HttpResponse(status=204)
    response["HX-Refresh"] = "true"
    response["HX-Trigger"] = json.dumps({"toast": toast})
    return response
