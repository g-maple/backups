import datetime
import typing
import re
from ...common.cookies import _COOKIE_EXPIRE_FORMAT

__all__ = [
    "HttpHeaders"
]
_QVALUE_REGEX = re.compile(b'\\s?([^,;]+)(?:;q=(-?[\\d\\.]+))?(?:,\\s?|$)')
_QVALUE_DEFAULT = 1.0
_HTTP_HEADER_KEY_CACHE = {}


class HttpHeaders(dict):
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def __getitem__(self, key: bytes) -> bytes:
        if key not in _HTTP_HEADER_KEY_CACHE:
            _HTTP_HEADER_KEY_CACHE[key] = key.upper()
        return dict.__getitem__(self, _HTTP_HEADER_KEY_CACHE[key])

    def __setitem__(self, key: bytes, val: typing.Union[bytes, typing.Iterable[bytes]]) -> None:
        if isinstance(val, int):
            val = [b'%d' % val]
        elif isinstance(val, bytes):
            val = [val]
        elif isinstance(val, datetime.datetime):
            val = [val.strftime(_COOKIE_EXPIRE_FORMAT).encode("utf-8")]
        if key not in _HTTP_HEADER_KEY_CACHE:
            _HTTP_HEADER_KEY_CACHE[key] = key.upper()
        dict.__setitem__(self, _HTTP_HEADER_KEY_CACHE[key], val)

    def __delitem__(self, key: bytes) -> None:
        dict.__delitem__(self, key.upper())

    def __contains__(self, key: bytes) -> bool:
        return dict.__contains__(self, key.upper())

    def __repr__(self):
        return "<HttpHeaders {}>".format(" ".join(["{}={}".format(key, val) for key, val in self.items()]))

    def get(self, key: bytes, default=None) -> typing.Union[None, typing.Iterable[bytes]]:
        return dict.get(self, key.upper(), default)

    def update(self, *args, **kwargs):
        for key, val in dict(*args, **kwargs).items():
            self[key] = val

    def qlist(self, key: bytes) -> typing.List[typing.Tuple[bytes, float]]:
        """
        Sorts a header into a list according to it's q-values.
        Items without q-values are valued highest.
        :param key: Header to get the qlist for.
        :return: List of items with their qvalue and their byte data sorted highest to lowest.
        """
        qlist = _QVALUE_REGEX.findall(b','.join(self[key]))
        for i in range(len(qlist)):
            item, qvalue = qlist[i]
            if qvalue == b'':
                qlist[i] = (item, _QVALUE_DEFAULT)
            else:
                qlist[i] = (item, float(qvalue))
        return sorted(qlist, key=lambda k: k[1], reverse=True)

    def to_bytes(self) -> bytes:
        return b'\r\n'.join((
            b'\r\n'.join([b'%b: %b' % (key, val) for val in list_val])
        ) for key, list_val in self.items())
