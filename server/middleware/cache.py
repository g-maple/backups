import datetime
import typing
from . import AbstractMiddleware
from ...proto.http import HttpRequest, HttpResponse
from ...proto.common.cookies import _COOKIE_EXPIRE_FORMAT

__all__ = [
    "CacheControlMiddleware",
    "CacheControlPolicy",
    "CACHE_CONTROL_PUBLIC",
    "CACHE_CONTROL_PRIVATE",
    "CACHE_CONTROL_NO_CACHE"
]
CACHE_CONTROL_PUBLIC = b'public'
CACHE_CONTROL_PRIVATE = b'private'
CACHE_CONTROL_NO_CACHE = b'no-cache, no-store'
_CACHE_METHODS = {b'GET'}

# Cache-Control max-age should not be greater than 1 year. RFC-compliant browsers may ignore values beyond.
# See http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9.3 for more information.
_MAX_AGE_MAXIMUM_VALUE = 31536000


class CacheControlPolicy:
    def __init__(self, cache_setting: bytes=CACHE_CONTROL_PRIVATE, max_age: int=None,
                 etag: typing.Callable[[HttpRequest], bytes]=None,
                 last_modified: typing.Callable[[HttpRequest], datetime.datetime]=None,
                 expires: typing.Callable[[HttpRequest], datetime.datetime]=None):

        self.cache_setting = cache_setting
        self.max_age = max_age
        if self.max_age is not None and self.max_age > _MAX_AGE_MAXIMUM_VALUE:
            self.max_age = _MAX_AGE_MAXIMUM_VALUE
        self.etag = etag
        self.last_modified = last_modified
        self.expires = expires

        self.cached_etag = None  # type: bytes
        self.cached_last_modified = None  # type: datetime.datetime
        self.cache_control_header = self.cache_setting
        if self.max_age is not None:
            self.cache_control_header += b', max-age=%d' % max_age

        self.not_modified = HttpResponse(status=b'Not Modified', status_code=304)
        self.not_modified.headers[b'Cache-Control'] = self.cache_control_header


class CacheControlMiddleware(AbstractMiddleware):
    def __init__(self, default: CacheControlPolicy):
        self.cache_policies = {}  # type: typing.Dict[bytes, CacheControlPolicy]
        self.default_policy = default  # type: CacheControlPolicy
        self._request_to_policy = {}  # type: typing.Dict[HttpRequest, CacheControlPolicy]
        AbstractMiddleware.__init__(self)

    def add_route(self, route: bytes, cache_policy: CacheControlPolicy):
        self.routes.add(route)
        self.cache_policies[route] = cache_policy
        route = route.rstrip(b'/')
        if len(route):
            self.routes.add(route)
            self.cache_policies[route] = cache_policy

    def should_be_applied(self, request: HttpRequest):
        return request.url.path in self.cache_policies and \
               b'no-cache' not in request.headers.get(b'Cache-Control', []) and \
               request.method in _CACHE_METHODS and (self.all_routes or request.url.path in self.routes)

    def before_handler(self, request: HttpRequest) -> typing.Optional[HttpResponse]:
        cache_policy = self.cache_policies.get(request.url.path, self.default_policy)
        self._request_to_policy[request] = cache_policy

        # Etag / If-None-Match
        if cache_policy.etag is not None and b'If-None-Match' in request.headers:
            cache_policy.cached_etag = cache_policy.etag(request)
            if cache_policy.cached_etag in request.headers[b'If-None-Match']:
                cache_policy.not_modified.headers[b'Etag'] = cache_policy.cached_etag
                return cache_policy.not_modified

        # Last-Modifed / If-Modified-Since
        if cache_policy.last_modified is not None and b'If-Modified-Since' in request.headers:
            cache_policy.cached_last_modified = cache_policy.last_modified(request)
            if datetime.datetime.strptime(request.headers[b'If-Modified-Since'][0].decode("utf-8"),
                                          _COOKIE_EXPIRE_FORMAT) > cache_policy.cached_last_modified:
                cache_policy.not_modified.headers[b'Last-Modified'] = cache_policy.cached_last_modified
                return cache_policy.not_modified

    def after_handler(self, request: HttpRequest, response: HttpResponse):
        if request in self._request_to_policy:
            cache_policy = self._request_to_policy[request]
            response.headers[b'Cache-Control'] = cache_policy.cache_control_header

            # Etag / If-None-Match
            if cache_policy.etag is not None:
                if cache_policy.cached_etag is None:
                    cache_policy.cached_etag = cache_policy.etag(request)
                response.headers[b'Etag'] = cache_policy.cached_etag

            # Last-Modified / If-Modified-Since
            if cache_policy.last_modified is not None:
                if cache_policy.cached_last_modified is None:
                    cache_policy.cached_last_modified = cache_policy.last_modified(request)
                response.headers[b'Last-Modified'] = cache_policy.cached_last_modified

            if cache_policy.expires is not None:
                expire_time = cache_policy.expires(request)
                if isinstance(expire_time, datetime.datetime):
                    response.headers[b'Expires'] = expire_time
                else:
                    response.headers[b'Expires'] = b'0'

            # Get rid of the request -> policy association.
            del self._request_to_policy[request]
