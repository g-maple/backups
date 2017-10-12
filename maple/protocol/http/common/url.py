import re
from typing import Dict

__all__ = [
    "Url"
]
_QUERY_REGEX = re.compile('([^=&]+)=([^=&]+)')


class Url:
    __slots__ = [
        'raw', 'schema', 'host', 'port', 'path', 'query', 'fragment',
        'user_info', 'followed', '_get_form', 'match_info'
    ]

    def __init__(self, raw: str=None, schema: str=None, host: str=None,
                 port: int=-1, path: str=None, query: str=None, fragment: str=None,
                 user_info: str=None):
        self.raw = raw
        self.schema = schema.lower() if schema is not None else ''
        self.host = host or ''
        self.port = port or -1
        self.path = path or '/'
        self.query = {key: value for key, value in _QUERY_REGEX.findall('' if query is None else query)}
        self.fragment = fragment or ''
        self.user_info = user_info or ''
        self.match_info: Dict[str, str] = {}
        self.followed = ''
        self._get_form = self.path + (('?' + query) if query else '')

    def get(self) -> str:
        return self._get_form

    def __repr__(self) -> str:
        return "<Url: raw={} schema={} host={} port={} path={} query={}, match_info={}, user_info={}>".format(
            self.raw, self.schema, self.host, self.port, self.path, self.query, self.match_info, self.user_info
        )

