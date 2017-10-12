import httptools
from .primitives import HttpMessage, HttpRequest
from ..abc import AbstractMessageParser

__all__ = [
    "HttpParser"
]


class HttpParser(AbstractMessageParser):
    def __init__(self, message=None):
        self._parser = None
        self._headers_done = False
        self._is_request = None
        AbstractMessageParser.__init__(self, message)

    def set_target(self, message: HttpMessage):
        """
        Sets the HttpMessage for the data to be parsed into.
        :param message: HttpRequest or HttpResponse to
        :return: None
        """
        if self._is_request is None:
            self._is_request = isinstance(message, HttpRequest)
        if self._is_request:
            self._parser = httptools.HttpRequestParser(message)
        else:
            self._parser = httptools.HttpResponseParser(message)
        self.message = message
        self._headers_done = False

    def feed_data(self, data: bytes):
        """
        Feed byte data into the parser.
        :param data: Data to be parsed.
        :return: None
        """
        self._parser.feed_data(data)
        if not self._headers_done and self.message.is_header_complete():
            self._headers_done = True
            if self._is_request:
                self.message.method = self._parser.get_method()
            else:
                self.message.status_code = self._parser.get_status_code()
            self.message.version = self._parser.get_http_version().encode("utf-8")