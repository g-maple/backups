from .primitives import HttpRequest
from ._parser import HttpParserUpgrade
from .parser import HttpParser
from ...abc import AbstractMessage, AbstractWebProtocol

__all__ = [
    "HttpProtocol"
]


class HttpProtocol(AbstractWebProtocol):
    def __init__(self,base):
        self.server = base.server
        self._version = None
        self._request = HttpRequest()
        self._parser = HttpParser(self._request)
        super().__init__(base)

    def receive_message(self, messag: AbstractMessage):
        pass

    def receive_data(self, data: bytes):
        if self._request is None:
            self._request = HttpRequest()
            self._parser.set_target(self._request)
        print(data)
        try:
            # self.base._cancle_connection_timeout()
            self._parser.feed_data(data)
        except HttpParserUpgrade:
            pass

        if self._request.is_complete():
            if self._version is None:
                self._version = self._request.version

            self.receive_message(self._request)
            self._request = None

    def send_message(self, meeage: AbstractMessage):
        pass
