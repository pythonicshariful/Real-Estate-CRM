"""
Transparent gzip compression + static cache headers.

The app ships ~700 KB of assets per page in development (Tailwind's JIT
runtime, Chart.js, FullCalendar, fonts). Flask does not compress by default,
so every byte went over the wire verbatim. This middleware gzips text
responses and caches the compressed bytes keyed on the file's mtime, which
takes a page from ~750 KB down to ~200 KB on the wire.

Pure standard library — no new dependency, keeps the cPanel deploy story.
"""

import gzip
import os
import threading

# Content types worth compressing. Images/video are already compressed.
COMPRESSIBLE = (
    'text/',
    'application/javascript',
    'application/json',
    'application/xml',
    'image/svg+xml',
    'application/manifest+json',
)

MIN_SIZE = 512           # below this the gzip header costs more than it saves
MAX_SIZE = 4 * 1024 * 1024

_cache = {}
_cache_lock = threading.Lock()


def _is_compressible(mimetype, size):
    if size < MIN_SIZE or size > MAX_SIZE:
        return False
    mt = (mimetype or '').lower()
    return any(mt.startswith(p) or p in mt for p in COMPRESSIBLE)


def _gzip_cached(key, payload):
    with _cache_lock:
        hit = _cache.get(key)
        if hit is not None:
            return hit
    out = gzip.compress(payload, compresslevel=6)
    with _cache_lock:
        if len(_cache) > 512:          # crude but bounded
            _cache.clear()
        _cache[key] = out
    return out


def init_compression(app):
    @app.after_request
    def _compress(response):
        try:
            if response.direct_passthrough:
                # send_file() streams; buffer it so we can compress
                response.direct_passthrough = False

            if response.status_code != 200:
                return response
            if response.headers.get('Content-Encoding'):
                return response
            if response.headers.get('Content-Range'):
                return response
            if 'gzip' not in (request_headers() or '').lower():
                return response

            payload = response.get_data()
            if not _is_compressible(response.mimetype, len(payload)):
                return response

            # Cache key: path + mtime when it is a file on disk
            filepath = response.headers.get('X-Accel-Redirect') or ''
            key = None
            try:
                from flask import request
                candidate = os.path.join(app.static_folder, request.path.lstrip('/'))
                if os.path.isfile(candidate):
                    key = (request.path, os.path.getmtime(candidate), len(payload))
            except Exception:
                key = None
            if key is None:
                key = (getattr(response, 'mimetype', ''), hash(payload))

            body = _gzip_cached(key, payload)
            if len(body) >= len(payload):
                return response

            response.set_data(body)
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Length'] = str(len(body))
            response.headers.add('Vary', 'Accept-Encoding')
        except Exception:
            app.logger.debug('compression skipped', exc_info=True)
        return response


def request_headers():
    try:
        from flask import request
        return request.headers.get('Accept-Encoding', '')
    except Exception:
        return ''


def init_cache_headers(app):
    @app.after_request
    def _cache_headers(response):
        try:
            from flask import request
            path = request.path
            if path.startswith(('/api/', '/uploads/')) or path == '/health':
                return response
            if response.status_code != 200:
                return response

            if path.startswith('/assets/'):
                # Fingerprint-free assets: allow reuse, revalidate in the background
                response.headers['Cache-Control'] = 'public, max-age=86400, must-revalidate'
            elif path.endswith('.html') or path == '/':
                # HTML must always be fresh — it references the JS/CSS
                response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        except Exception:
            pass
        return response


def init_performance(app):
    init_compression(app)
    init_cache_headers(app)
