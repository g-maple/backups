import datetime
import typing
from .abc import AbstractCookieJarStorage
from ...proto.common.cookies import Cookie, _COOKIE_EXPIRE_FORMAT
from ...proto.http.primitives.message import _COOKIE_REGEX

__all__ = [
    "TemporaryCookieJarStorage",
    "FileCookieJarStorage"
]


class TemporaryCookieJarStorage(AbstractCookieJarStorage):
    def __init__(self):
        AbstractCookieJarStorage.__init__(self)

    def load_all_cookies(self) -> typing.List[Cookie]:
        pass

    def save_all_cookies(self, cookies: typing.List[Cookie]):
        pass


class FileCookieJarStorage(AbstractCookieJarStorage):
    def __init__(self, file_path: str):
        AbstractCookieJarStorage.__init__(self)
        self._file_path = file_path

    def load_all_cookies(self) -> typing.List[Cookie]:
        cookie_file = open(self._file_path, "rb")
        cookies = []

        for cookie_bytes in cookie_file.read().split(b'\r\n'):
            if cookie_bytes == b'':
                continue
            values, domain, path, expires, max_age, http_only, secure = tuple(cookie_bytes.split(b'\0'))
            cookie = Cookie()
            for key, value in _COOKIE_REGEX.findall(values):
                cookie.values[key] = value
            cookie.domain = None if domain == b'' else domain
            cookie.path = None if path == b'' else path
            cookie.http_only = http_only == b'1'
            cookie.secure = secure == b'1'
            cookie.max_age = None if max_age == b'' else int(max_age.decode("utf-8"))
            cookie.expires = None if expires == b'' else datetime.datetime.strptime(expires.decode("utf-8"), _COOKIE_EXPIRE_FORMAT)
            cookies.append(cookie)

        cookie_file.close()
        return cookies

    def save_all_cookies(self, cookies: typing.List[Cookie]):
        cookie_file = open(self._file_path, "wb")
        cookie_file.truncate()
        for cookie in cookies:
            cookie_bytes = b'\0'.join([
                b';'.join([b'%b=%b' % (key, val) for key, val in cookie.values.items()]),
                b'' if cookie.domain is None else cookie.domain,
                b'' if cookie.path is None else cookie.path,
                b'' if cookie.expires is None else cookie.expires.strftime(_COOKIE_EXPIRE_FORMAT).encode("utf-8"),
                b'' if cookie.max_age is None else b'%d' % cookie.max_age,
                b'1' if cookie.http_only else b'0',
                b'1' if cookie.secure else b'0',
            ]) + b'\r\n'
            cookie_file.write(cookie_bytes)
        cookie_file.close()
