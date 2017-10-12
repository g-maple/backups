import abc
import types
import typing
from ...proto.http import HttpRequest, HttpResponse

__all__ = [
    "AbstractMiddleware"
]


class AbstractMiddleware(abc.ABC):
    def __init__(self):
        self.all_routes = False
        self.routes = set()

    @abc.abstractmethod
    def before_handler(self, request: HttpRequest) -> typing.Union[types.CoroutineType, typing.Optional[HttpResponse]]:
        pass

    @abc.abstractmethod
    def after_handler(self, request: HttpRequest, response: HttpResponse) -> typing.Optional[types.CoroutineType]:
        pass

    def should_be_applied(self, request: HttpRequest):
        return self.all_routes or request.url.path in self.routes

    def add_route(self, route: bytes, *args, **kwargs):
        self.routes.add(route)
        route = route.rstrip(b'/')
        if len(route):
            self.routes.add(route)

    def add_routes(self, routes: typing.Iterable[bytes], *args, **kwargs):
        for route in routes:
            self.add_route(route, *args, **kwargs)
