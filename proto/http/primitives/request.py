import httptools
import typing
from .message import HttpMessage
from ...common import Url

__all__ = [
    "HttpRequest"
]


class HttpRequest(HttpMessage):
    def __init__(self, headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None):
        HttpMessage.__init__(self)
        if headers is not None:
            for key, val in headers.items():
                self.headers[key] = val
        self.url = None  # type: Url
        self.method = b''
        self.session = None

    def on_url(self, raw_url: bytes):
        if raw_url != b'':
            url = httptools.parse_url(raw_url)
            self.url = Url(raw_url, url.schema, url.host, url.port, url.path, url.query, url.fragment, url.userinfo)
            if self.cookies:
                for cookie in self.cookies.values():
                    cookie.path = url.path

    def to_bytes(self) -> bytes:
        parts = [b'%b %b HTTP/%b' % (self.method, self.url.get(), self.version)]
        if self.headers:
            parts.append(self.headers.to_bytes())
        if self.cookies:
            parts.append(self.cookies.to_bytes())
        parts.append(b'')
        parts.append(self.body)
        return b'\r\n'.join(parts)

    def __repr__(self):
        return "<HttpRequest version={} method={} url={} headers={}>".format(self.version, self.method, self.url, self.headers)
