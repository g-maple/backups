import typing
from .message import HttpMessage

__all__ = [
    "HttpResponse",
    "TemplateHttpResponse"
]


class HttpResponse(HttpMessage):
    def __init__(self, headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None,
                 status_code: int=0, status: bytes=b''):
        HttpMessage.__init__(self)
        if headers is not None:
            for key, val in headers.items():
                self.headers[key] = val
        self.status_code = status_code
        self.status = status

    def on_status(self, status: bytes):
        self.status = status

    def to_bytes(self) -> bytes:
        parts = [b'HTTP/%b %d %b' % (self.version, self.status_code, self.status)]
        if self.headers:
            parts.append(self.headers.to_bytes())
        if self.cookies:
            parts.append(self.cookies.to_bytes(set_cookie=True))
        parts.append(b'')
        parts.append(self.body)
        return b'\r\n'.join(parts)

    def __repr__(self):
        return "<HttpResponse status={} status_code={} headers={}>".format(self.status, self.status_code, self.headers)


class TemplateHttpResponse(HttpResponse):
    def __init__(self, headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None,
                 status_code: int = 0, status: bytes = b''):
        self.template_info = {}  # typing.Dict[str, typing.Any]
        HttpResponse.__init__(self, headers, status_code, status)
