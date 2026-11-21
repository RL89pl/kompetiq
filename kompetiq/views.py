from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import connection


@ensure_csrf_cookie
def spa(request, *args, **kwargs):
    """Serwuje index.html zbudowanego frontendu (React). Assety idą przez /static/spa/ (nginx)."""
    index = settings.FRONTEND_DIST / 'index.html'
    if not index.exists():
        return HttpResponse('Frontend nie jest zbudowany (npm run build w katalogu frontend/).', status=503)
    resp = HttpResponse(index.read_text(encoding='utf-8'))
    resp['Cache-Control'] = 'no-cache'
    return resp


def health(request):
    with connection.cursor() as c:
        c.execute('SELECT 1')
    return JsonResponse({'status': 'ok'})
