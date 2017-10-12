import typing
from .abc import AbstractMiddleware
from ...proto.http import HttpRequest, HttpResponse

__all__ = [
    "CorsMiddleware",
    "CorsPolicy"
]
_DEFAULT_ALLOW_ORIGIN = b'*'
_DEFAULT_ALLOW_METHODS = [b'POST', b'GET', b'OPTIONS']
_CORS_METHODS = {b'GET', b'POST', b'OPTIONS'}


class CorsPolicy:
    def __init__(self, origin: bytes=_DEFAULT_ALLOW_ORIGIN,
                 methods: bytes=_DEFAULT_ALLOW_METHODS,
                 headers: bytes=None, max_age: int=None):
        self.origin = origin
        self.methods = methods
        self.headers = headers
        self.max_age = max_age


class CorsMiddleware(AbstractMiddleware):
    def __init__(self, default: CorsPolicy=None):
        self.cors_policies = {}  # type: typing.Dict[bytes, CorsPolicy]
        self.default_policy = default  # type: CorsPolicy
        AbstractMiddleware.__init__(self)

    def add_route(self, route: bytes, cors_policy):
        self.routes.add(route)
        self.cors_policies[route] = cors_policy
        route = route.rstrip(b'/')
        if len(route):
            self.routes.add(route)
            self.cors_policies[route] = cors_policy

    def should_be_applied(self, request: HttpRequest):
        return (self.all_routes or request.url.path in self.routes) and \
               request.method in self.cors_policies.get(request.url.path, self.default_policy).methods

    def before_handler(self, request: HttpRequest):
        pass

    def after_handler(self, request: HttpRequest, response: HttpResponse):
        cors_policy = self.cors_policies.get(request.url.path, self.default_policy)
        if cors_policy.origin is not None:
            response.headers[b'Access-Control-Allow-Origin'] = cors_policy.origin
        if cors_policy.methods is not None:
            response.headers[b'Access-Control-Allow-Methods'] = cors_policy.methods
        if cors_policy.headers is not None:
            response.headers[b'Access-Control-Allow-Headers'] = cors_policy.headers
        if cors_policy.max_age is not None:
            response.headers[b'Access-Control-Max-Age'] = cors_policy.max_age
