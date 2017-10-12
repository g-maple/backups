from .storage import AbstractSessionStorage
from ..abc import AbstractMiddleware
from ....proto.http import HttpRequest, HttpResponse
from ....proto.common import Cookie

__all__ = [
    "SessionMiddleware"
]


class SessionMiddleware(AbstractMiddleware):
    def __init__(self, storage: AbstractSessionStorage):
        self.storage = storage
        AbstractMiddleware.__init__(self)

    def before_handler(self, request: HttpRequest):
        cookie_session = request.cookies.all().get(self.storage.cookie_key)
        if cookie_session is not None:
            request.session = self.storage.load_session(cookie_session)
        else:
            request.session = self.storage.new_session()

    def after_handler(self, request: HttpRequest, response: HttpResponse):
        if request.session is not None:
            session_cookie = Cookie()
            session_cookie.values[self.storage.cookie_key] = self.storage.save_session(request.session)
            session_cookie.domain = self.storage.domain
            session_cookie.path = self.storage.path
            session_cookie.max_age = self.storage.max_age
            session_cookie.http_only = self.storage.http_only
            session_cookie.secure = self.storage.secure
            response.cookies.add(session_cookie)
