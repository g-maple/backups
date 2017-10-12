from . import common, http, http2, hyper2, websockets
from .abc import *

__all__ = [
    "common",
    "http",
    "http2",
    "websockets",
    "hyper2",

    "PROTOCOL_HTTP_1_1",
    "PROTOCOL_HTTP_2",
    "PROTOCOL_SPDY",
    "PROTOCOL_WEBSOCKETS",
    "PROTOCOL_DEFAULT"
] + abc.__all__

PROTOCOL_HTTP_1_1 = "http/1.1"
PROTOCOL_HTTP_2 = "h2"
PROTOCOL_SPDY = "spdy/3"
PROTOCOL_WEBSOCKETS = "websockets"
PROTOCOL_DEFAULT = "default"