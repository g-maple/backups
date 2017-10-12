import datetime
from .url import Url
from typing import Dict, Optional, Tuple

__all__ = [
    "Cookies",
    "Cookie",
    "_COOKIE_EXPIRE_FORMAT"
]
_EPOCH = datetime.datetime.fromtimestamp(0)
_COOKIE_EXPIRE_FORMAT = "%a,%d %b %Y %H:%M:%S GMT"


class Cookie:
    __slots__ = [
        'values', 'domain', 'path', 'expires', '_max_age', 'http_only', 'secure', '_max_age_set'
    ]

    def __init__(self, domain: str=None, path: str=None, expires: datetime.datetime=None,
                 max_age: int=None, http_only: bool=False, secure: bool=False):
        self.values: Dict[str, str] = {}
        self.domain = domain
        self.path = path
        self.expires = expires
        self._max_age = max_age
        self.http_only = http_only or True  # 默认仅http访问
        self.secure = secure
        self._max_age_set = datetime.datetime.utcnow()

    def __eq__(self, other) -> bool:
        return isinstance(other, Cookie) and self.domain == other.domain and self.path == other.path

    @property
    def max_age(self) -> Optional[int]:
        return self._max_age

    @max_age.setter
    def max_age(self, max_age: Optional[int, None]) -> None:
        self._max_age = max_age
        self._max_age_set = datetime.datetime.utcnow()
        return

    def expire(self) -> None:
        """
        过期的Cookie 和 删除所有的值
        :return: None
        """
        self.expires = _EPOCH
        self.max_age = 0
        for key in self.values.keys():
            self.values[key] = ''
        return

    def _expiration_datetime(self) -> Optional[datetime.datetime, None]:
        """
        返回HttpCookie过期时的datetime对象。如果Cookie已经过期，那么它在过期时返回。
        如果没有任何值返回，则表示没有当前值对Cookie的时间表过期。
        :return: Datetime object or None.
        """
        _expire_times = []
        if self._max_age is not None:
            _expire_times.append(self._max_age_set + datetime.timedelta(seconds=self._max_age))
        if self.expires is not None:
            _expire_times.append(self.expires)
        if not _expire_times:
            return None
        else:
            return min(_expire_times)

    def is_expired(self) -> bool:
        _expire_time = self._expiration_datetime()
        return _expire_time is not None and datetime.datetime.utcnow() > _expire_time

    def is_allowed_for_url(self, url: Url) -> bool:
        # 先检查 cookie 时否仅 https 访问
        if self.secure and url.schema != 'https':
            return False

        # 检查这是主域名还是子域名
        if self.domain is not None:
            _url_domins = url.host.split('.')
            _cookie_domins = self.domain.split('.')
            if _cookie_domins[0] == '':
                _cookie_domins = _cookie_domins[1:]  # This is to remove the '.google.com' "fix" for old browsers.
            _len_cookie_domains = len(_cookie_domins)
            if _len_cookie_domains > len(_url_domins):
                return False
            for i in range(-1, -_len_cookie_domains-1, -1):
                if _url_domins[i] != _cookie_domins[i]:
                    return False

        # 检查这是不是一个有效的子路径
        if self.path is not None and not url.path.startswith(self.path):
            return False

        return True

    def __repr__(self) -> str:
        return "<HttpCookie: values={} domain={} path={]>".format(self.values, self.domain, self.path)


class Cookies(dict):
    def __setitem__(self, key: Tuple[str, str], value: Cookie) -> None:
        super().__setitem__(key, value)

    def __getitem__(self, item: Tuple[str, str]) -> Cookie:
        return super().__getitem__(item)

    def add(self, cookie: Cookie) -> None:
        self[(cookie.domain, cookie.path)] = cookie

    def remove(self, cookie: Cookie) -> None:
        _cookie_key = (cookie.domain, cookie.path)
        if _cookie_key in self:
            super().__delattr__(_cookie_key)

    def all(self) -> Dict[str, str]:
        _values = {}
        for _cookie in self.values():
            for key, value in _cookie.values.items():
                _values[key] = value
        return _values

    def to_bytes(self, set_cookie: bool=False) -> bytes:
        if set_cookie:
            _all_cookie_crumbs = []
            for _cookie in self.values():
                _cookie_crumbs = ['Set-Cookie:']
                for key, value in _cookie.values.items():
                    _cookie_crumbs.append(f'{key}={value};')

                if _cookie.domain is not None:
                    _cookie_crumbs.append(f'Domain={_cookie.domain};')
                if _cookie.path is not None:
                    _cookie_crumbs.append(f'Path={_cookie.path};')
                if _cookie.expires is not None:
                    _cookie_crumbs.append('Expires={!r};'.format(_cookie.expires.strftime(_COOKIE_EXPIRE_FORMAT)))
                if _cookie.max_age is not None:
                    _cookie_crumbs.append(f'MaxAge={_cookie.max_age};')
                if _cookie.http_only is not None:
                    _cookie_crumbs.append('HttpOnly;')
                if _cookie.secure is not None:
                    _cookie_crumbs.append('Secure;')

                _all_cookie_crumbs.append(' '.join(_cookie_crumbs))
            return '\r\n'.join(_all_cookie_crumbs).encode('utf-8')
        else:
            _all_values = {}
            for _cookie in self.values():
                for key, value in _cookie.values.items():
                    if key not in _all_values:
                        _all_values[key] = value

            return ('Cookie: ' + ' '.join(
                ['%s=%s;' % (key, _all_values[key]) for key in _all_values]
            )).encode('utf-8')
