from ._parser import HttpResponseParser, HttpRequestParser
from typing import Optional
from .primitives import HttpRequest, HttpMessage
from ...abc import AbstractMessageParser, AbstractMessage

__all__ = [
    "HttpParser"
]


class HttpParser(AbstractMessageParser):
    def __init__(self, message: AbstractMessage=None):
        self._parser: Optional[HttpRequestParser, HttpResponseParser, None] = None
        self._headers_done: bool = False
        self._is_request = None
        super().__init__(message)

    def set_target(self, message: HttpMessage) -> None:
        """
        根据AbstractMessage类型设置数据解析器
        :param message: HttpRequest or HttpResponse to
        :return: None
        """
        if self._is_request is None:
            self._is_request = isinstance(message, HttpRequest)

        if self._is_request:
            self._parser = HttpRequestParser(message)
        else:
            self._parser = HttpResponseParser(message)
        self.message = message
        self._headers_done = False

        return

    def feed_data(self, data: bytes) -> None:
        """
        将字节数据传入解析器
        :param data: 要解析的数据
        :return: None
        """
        self._parser.feed_data(data)
        # if not self._headers_done and self.message.is_header_complete():
        #     self._headers_done = True
        #     if self._is_request:
        #         self.message.method = self._parser.get_method()
        #     else:
        #         self.message.status_code = self._parser.get_status_code()
        #     self.message.version = self._parser.get_http_version().encode("utf-8")



