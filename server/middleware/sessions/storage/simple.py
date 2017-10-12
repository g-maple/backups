import datetime
import json
from .abc import AbstractSessionStorage, _COOKIE_KEY
from ..session import Session

__all__ = [
    "SimpleSessionStorage"
]


class SimpleSessionStorage(AbstractSessionStorage):
    def __init__(self, cookie_key: bytes=_COOKIE_KEY, domain: bytes=None, path: bytes=b'/',
                 expires: datetime.datetime=None, max_age: int=None, http_only: bool=True, secure: bool=False):
        AbstractSessionStorage.__init__(self, cookie_key, domain, path, expires, max_age, http_only, secure)

    def load_session(self, cookie_session: bytes):
        session_data = None
        try:
            session_data = json.loads(cookie_session.decode("utf-8"))
        except UnicodeDecodeError:
            pass
        except json.JSONDecodeError:
            pass
        if session_data is None:
            return self.new_session()
        else:
            return Session(None, session_data)

    def save_session(self, session: Session) -> bytes:
        return json.dumps(session).encode("utf-8")

    def new_session(self) -> Session:
        return Session(None, {})
