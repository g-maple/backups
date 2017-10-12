import mako.lookup
from .abc import AbstractTemplatingMiddleware

__all__ = [
    "MakoTemplatingMiddleware"
]


class MakoTemplatingMiddleware(AbstractTemplatingMiddleware):
    def __init__(self, lookup: mako.lookup.TemplateLookup):
        self.lookup = lookup
        AbstractTemplatingMiddleware.__init__(self)

    def render_template(self, route: bytes, environment: dict) -> bytes:
        return self.lookup.get_template(self.route_templates[route]).render(**environment).encode(self.encoding)
