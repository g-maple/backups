import abc
import datetime
from ..session import Session

__all__ = [
    "AbstractSessionStorage"
]
_COOKIE_KEY = b'stormhttp_session'


class AbstractSessionStorage(abc.ABC):
    def __init__(self, cookie_key: bytes=_COOKIE_KEY, domain: bytes=None, path: bytes=b'/',
                 expires: datetime.datetime=None, max_age: int=None, http_only: bool=True, secure: bool=False):
        self.cookie_key = cookie_key
        self.domain = domain
        self.path = path
        self.expires = expires
        self.max_age = max_age
        self.http_only = http_only
        self.secure = secure

    @abc.abstractmethod
    def load_session(self, cookie_session: bytes) -> Session:
        pass

    @abc.abstractmethod
    def save_session(self, session: Session) -> bytes:
        pass

    @abc.abstractmethod
    def new_session(self) -> Session:
        pass


