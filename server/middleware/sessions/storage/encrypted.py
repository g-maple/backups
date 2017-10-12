import base64
import datetime
import fernet
import json
from .abc import AbstractSessionStorage, _COOKIE_KEY
from ..session import Session

__all__ = [
    "EncryptedSessionStorage"
]


class EncryptedSessionStorage(AbstractSessionStorage):
    def __init__(self, secret_key: bytes, cookie_key: bytes=_COOKIE_KEY, domain: bytes=None, path: bytes=b'/',
                 expires: datetime.datetime=None, max_age: int=None, http_only: bool=True, secure: bool=False):
        self._fernet = fernet.Fernet(base64.urlsafe_b64encode(secret_key))
        AbstractSessionStorage.__init__(self, cookie_key, domain, path, expires, max_age, http_only, secure)

    def load_session(self, cookie_session: bytes):
        session_data = None
        try:
            session_data = json.loads(self._fernet.decrypt(cookie_session).decode("utf-8"))
        except UnicodeDecodeError:
            pass
        except json.JSONDecodeError:
            pass
        except fernet.InvalidToken:
            pass
        except fernet.InvalidSignature:
            pass
        if session_data is None:
            return self.new_session()
        else:
            return Session(None, session_data)

    def save_session(self, session: Session) -> bytes:
        return self._fernet.encrypt(json.dumps(session).encode("utf-8"))

    def new_session(self) -> Session:
        return Session(None, {})
