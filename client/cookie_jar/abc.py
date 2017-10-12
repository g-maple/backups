import abc
import typing
from ...proto.common import Cookie, Cookies, Url

__all__ = [
    "AbstractCookieJarStorage",
    "AbstractCookieJar"
]


class AbstractCookieJarStorage(abc.ABC):
    @abc.abstractmethod
    def load_all_cookies(self) -> typing.List[Cookie]:
        pass

    @abc.abstractmethod
    def save_all_cookies(self, cookies: typing.List[Cookie]) -> None:
        pass


class AbstractCookieJar(abc.ABC):
    def __init__(self, storage: typing.Optional[AbstractCookieJarStorage]):
        self.storage = storage

    @abc.abstractmethod
    def load_all_cookies(self) -> None:
        pass

    @abc.abstractmethod
    def save_all_cookies(self) -> None:
        pass

    @abc.abstractmethod
    def get_cookies_for_url(self, url: Url) -> Cookies:
        pass

    @abc.abstractmethod
    def update_cookies(self, url: Url, cookies: Cookies):
        pass
