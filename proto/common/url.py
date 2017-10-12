import re
import typing

__all__ = [
    "Url"
]
_QUERY_REGEX = re.compile(b'([^=&]+)=([^=&]+)')


class Url:
    def __init__(self, raw: bytes=b'', schema: bytes=b'', host: bytes=b'', port: int=-1, path: bytes=b'',
                 query: bytes=b'', fragment: bytes=b'', user_info: bytes=b''):
        self.raw = raw
        self.schema = schema.lower() if schema is not None else b''
        self.host = host if host is not None else b''
        self.port = port if port is not None else -1
        self.path = path if (path is not None and path != b'') else b'/'
        self.query = {key: val for key, val in _QUERY_REGEX.findall(b'' if query is None else query)}
        self.fragment = fragment if fragment is not None else b''
        self.user_info = user_info if user_info is not None else b''
        self.match_info = {}  # type: typing.Dict[bytes, bytes]
        self.followed = b''
        self._get_form = self.path + ((b'?' + query) if query else b'')

    def get(self) -> bytes:
        return self._get_form

    def __repr__(self):
        return "<Url raw={} schema={} host={} port={} path={} query={}, match_info={}, user_info={}>".format(
            self.raw, self.schema, self.host, self.port, self.path, self.query, self.match_info, self.user_info
        )
