import abc
import datetime
from .abc import AbstractSessionStorage, _COOKIE_KEY
from ..session import Session

__all__ = [
    "AbstractFetchableSessionStorage"
]


class AbstractFetchableSessionStorage(AbstractSessionStorage):
    def __init__(self, cookie_key: bytes=_COOKIE_KEY, domain: bytes=None, path: bytes=b'/',
                 expires: datetime.datetime=None, max_age: int=None, http_only: bool=True, secure: bool=False):
        """
        AbstractFetchableSessionStorage is to be used for implementing Session
        storage models that require performing a lookup to acquire Session data.
        """
        AbstractSessionStorage.__init__(self, cookie_key, domain, path, expires, max_age, http_only, secure)

    def load_session(self, cookie_session: bytes) -> Session:
        try:
            return Session(cookie_session, self.fetch_session_data(cookie_session))
        except Exception:
            return self.new_session()

    def save_session(self, session: Session) -> bytes:
        self.store_session_data(session.identity, session)
        return session.identity

    @abc.abstractmethod
    def fetch_session_data(self, session_id: bytes) -> dict:
        pass

    @abc.abstractmethod
    def store_session_data(self, session_id: bytes, session_data: dict) -> None:
        pass
