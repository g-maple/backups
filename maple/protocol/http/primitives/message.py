import re
import datetime
from ....abc import AbstractMessage
from ..common import Cookie, Cookies, _COOKIE_EXPIRE_FORMAT
# from .headers import HttpHeaders

_COOKIE_REGEX = re.compile('([^\\s=;]+)(?:=([^;]+))?(?:;|$)')
_COOKIE_META = ['domain', 'path', 'expiers', 'maxage', 'httponly', 'secure']


class HttpMessage(AbstractMessage):
    def __init__(self):
        self.headers: dict = {}
        self.cookies: dict = Cookies()
        self.version: str = None
        self._extra: dict = {}

        self._body: str = ''
        self._body_len: int = 0
        self._body_buffer: list = []
        self._header_buffer: list = []
        self._is_header_complete: bool = False
        self._is_complete: bool = False
        super().__init__()

    def __len__(self) -> int:
        return self._body_len

    def is_complete(self) -> bool:
        """
        判断整个报文是否解析完成
        :return: bool
        """
        return self._is_complete

    def is_header_complete(self) -> bool:
        """
        判断报头是否解析完成
        :return: bool
        """
        return self._is_header_complete

    def on_header(self, name: bytes, value: bytes) -> None:
        """
        开始解析报头，但不包含起始行, 并将字节数据解码成字符串放入缓冲区
        :param name:
        :param value:
        :return:
        """
        self._header_buffer.append((name.decode("utf-8"), value.decode("utf-8")))

    def on_headers_complete(self) -> None:
        _headers = {}
        for key, value in self._header_buffer:
            if key in _headers:
                _headers[key].append(value)
            else:
                _headers[key] = [value]

        self.headers.update(_headers)

        if 'Cookie' in self.headers:

            # 添加一个单一的 cookie 到 'Cookie' 头
            _cookie = Cookie(domain=_headers.get('Host', [None])[0])

            for _cookie_header in self.headers['Cookie']:
                for key, value in _COOKIE_REGEX.findall(_cookie_header):
                    _cookie.values[key] = value

            self.cookies.add(_cookie)
            del self.headers['Cookie']

        elif 'Set-Cookie' in self.headers:

            for _cookie_header in self.headers['Set-Cookie']:
                _cookie = Cookie()
                for key, value in _COOKIE_REGEX.findall(_cookie_header):
                    _key_lower = key.lower()
                    if _key_lower in _COOKIE_META:
                        if _key_lower == 'secure':
                            _cookie.secure = True
                        elif _key_lower == 'httponly':
                            _cookie.http_only = True
                        elif _key_lower == 'domain':
                            _cookie.domain = value
                        elif _key_lower == 'path':
                            _cookie.path = value
                        elif _key_lower == 'expires':
                            try:
                                _cookie.expires = datetime.datetime.strptime(value, _COOKIE_EXPIRE_FORMAT)
                            except ValueError:
                                pass
                        else:
                            try:
                                _cookie.max_age = int(value)
                            except ValueError:
                                pass
                    else:
                        _cookie.values[key] = value

                self.cookies.add(_cookie)
            del self.headers['Set-Cookie']

        self._is_header_complete = True

    def on_body(self, body: bytes) -> None:
        """
        将body数据解码为字符串并存入缓冲区
        :param body:
        :return:
        """
        self._body_buffer.append(body.decode('utf-8'))

    def on_message_complete(self) -> None:
        self._body = ''.join(self._body_buffer)
        self._body_len = len(self._body)
        self._is_complete = True

    def to_bytes(self) -> bytes:
        raise NotImplementedError("HttpMessage.to_bytes() is not implemented.")
