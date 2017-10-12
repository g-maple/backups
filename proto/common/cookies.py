import datetime
import typing
from .url import Url

__all__ = [
    "Cookie",
    "Cookies"
]
_EPOCH = datetime.datetime.fromtimestamp(0)
_COOKIE_EXPIRE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


class Cookie:
    def __init__(self, domain: typing.Optional[bytes]=None, path: typing.Optional[bytes]=None,
                 expires: typing.Optional[datetime.datetime]=None, max_age: typing.Optional[int]=None,
                 http_only: bool=False, secure: bool=False):
        self.values = {}  # type: typing.Dict[bytes, bytes]
        self.domain = domain
        self.path = path
        self.expires = expires
        self._max_age = max_age
        self.http_only = http_only
        self.secure = secure
        self._max_age_set = datetime.datetime.utcnow()

    def __eq__(self, other) -> bool:
        return isinstance(other, Cookie) and self.domain == other.domain and self.path == other.path

    @property
    def max_age(self) -> typing.Optional[int]:
        return self._max_age

    @max_age.setter
    def max_age(self, max_age: typing.Optional[int]):
        self._max_age = max_age
        self._max_age_set = datetime.datetime.utcnow()

    def expire(self) -> None:
        """
        Expires the cookie and removes all the values.
        :return: None
        """
        self.expires = _EPOCH
        self.max_age = 0
        for key in self.values.keys():
            self.values[key] = b''

    def expiration_datetime(self) -> typing.Optional[datetime.datetime]:
        """
        Returns the datetime object for when the HttpCookie will expire.
        If the HttpCookie is already expired, then it returns when it expired.
        If a None value is returned, it indicates that there is not current
        schedule for the HttpCookie to expire.
        :return: Datetime object or None.
        """
        expire_times = []
        if self._max_age is not None:
            expire_times.append(self._max_age_set + datetime.timedelta(seconds=self._max_age))
        if self.expires is not None:
            expire_times.append(self.expires)
        if not expire_times:
            return None
        else:
            return min(expire_times)

    def is_expired(self) -> bool:
        expire_time = self.expiration_datetime()
        return expire_time is not None and datetime.datetime.utcnow() > expire_time

    def is_allowed_for_url(self, url: Url) -> bool:

        # First check to see if the cookie is for HTTPS only.
        if self.secure and url.schema != b'https':
            return False

        # Check that this is either a domain or sub-domain.
        if self.domain is not None:
            url_domains = url.host.split(b'.')
            cookie_domains = self.domain.split(b'.')
            if cookie_domains[0] == b'':  # This is to remove the '.google.com' "fix" for old browsers.
                cookie_domains = cookie_domains[1:]
            len_cookie_domains = len(cookie_domains)
            if len_cookie_domains > len(url_domains):
                return False
            for i in range(-1, -len_cookie_domains-1, -1):
                if url_domains[i] != cookie_domains[i]:
                    return False

        # Check this this is either a valid sub-path.
        if self.path is not None and not url.path.startswith(self.path):
            return False

        return True

    def __repr__(self):
        return "<HttpCookie values={} domain={} path={}>".format(self.values, self.domain, self.path)


class Cookies(dict):
    def __setitem__(self, key: typing.Tuple[bytes, bytes], value: Cookie) -> None:
        dict.__setitem__(self, key, value)

    def __getitem__(self, key: typing.Tuple[bytes, bytes]) -> Cookie:
        return dict.__getitem__(self, key)

    def add(self, cookie: Cookie):
        self[(cookie.domain, cookie.path)] = cookie

    def remove(self, cookie: Cookie):
        cookie_key = (cookie.domain, cookie.path)
        if cookie_key in self:
            dict.__delitem__(self, cookie_key)

    def all(self) -> typing.Dict[bytes, bytes]:
        values = {}
        for cookie in self.values():
            for key, value in cookie.values.items():
                values[key] = value
        return values

    def to_bytes(self, set_cookie: bool=False) -> bytes:
        if set_cookie:
            all_cookie_crumbs = []
            for cookie in self.values():
                cookie_crumbs = [b'SET-COOKIE:']
                for key, value in cookie.values.items():
                    cookie_crumbs.append(b'%b=%b;' % (key, value))

                if cookie.domain is not None:
                    cookie_crumbs.append(b'Domain=%b;' % cookie.domain)
                if cookie.path is not None:
                    cookie_crumbs.append(b'Path=%b;' % cookie.path)
                if cookie.expires is not None:
                    cookie_crumbs.append(b'Expires=%b;' % cookie.expires.strftime(_COOKIE_EXPIRE_FORMAT).encode("utf-8"))
                if cookie.max_age is not None:
                    cookie_crumbs.append(b'MaxAge=%d;' % cookie.max_age)
                if cookie.http_only:
                    cookie_crumbs.append(b'HttpOnly;')
                if cookie.secure:
                    cookie_crumbs.append(b'Secure;')

                all_cookie_crumbs.append(b' '.join(cookie_crumbs))
            return b'\r\n'.join(all_cookie_crumbs)
        else:
            all_values = {}
            for cookie in self.values():
                for key, value in cookie.values.items():
                    if key not in all_values:
                        all_values[key] = value
            return b'COOKIE: ' + b' '.join([b'%b=%b;' % (key, all_values[key]) for key in all_values])
