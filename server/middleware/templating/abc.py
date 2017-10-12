import abc
import typing
from .. import AbstractMiddleware
from ....proto.http import HttpRequest, HttpResponse, TemplateHttpResponse

__all__ = [
    "AbstractTemplatingMiddleware"
]


class AbstractTemplatingMiddleware(AbstractMiddleware):
    def __init__(self, encoding="utf-8"):
        self.encoding = encoding
        self.route_templates = {}  # type: typing.Dict[bytes, str]
        AbstractMiddleware.__init__(self)

    def add_route(self, route: bytes, template_name: str):
        self.routes.add(route)
        self.route_templates[route] = template_name
        route = route.rstrip(b'/')
        if len(route):
            self.routes.add(route)
            self.route_templates[route] = template_name

    @abc.abstractmethod
    def render_template(self, route: bytes, environment: dict) -> bytes:
        pass

    def before_handler(self, request: HttpRequest):
        pass

    def after_handler(self, request: HttpRequest, response: HttpResponse):
        if isinstance(response, TemplateHttpResponse):
            try:
                if "request" not in response.template_info:
                    response.template_info["request"] = request
                if "response" not in response.template_info:
                    response.template_info["response"] = response
                response.body = self.render_template(request.url.followed, response.template_info)
                if b'Content-Type' not in response.headers:
                    response.headers[b'Content-Type'] = b'text/html; charset=utf-8'
            except Exception as error:
                response.body = str(error).encode("utf-8")
                response.status_code = 500
                response.status = b'Internal Server Error'
