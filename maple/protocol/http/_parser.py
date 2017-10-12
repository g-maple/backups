import abc
from .primitives import HttpMessage
from ...utils import ensure_bytes, MapleError

__all__ = [
    "ParseError",
    "InvalidMessage",
    "EntityTooLarge",
    "HttpParserUpgrade",
    "HttpRequestParser",
    "HttpResponseParser"
]

class ParseError(MapleError):
    """
    所有解析错误都基于这个类
    """
    pass


class InvalidMessage(ParseError):
    """
    当消息不是一个有效消息时引发此错误
    """
    pass


class EntityTooLarge(ParseError):
    """
    信息过大，不能处理
    """
    pass


class HttpParserUpgrade(ParseError):
    """
    当协议请求升级时抛出错误
    """
    pass


class AbstractHttpParser(abc.ABC):
    def __init__(self, message: HttpMessage):
        """
        message对象可选AP：
        on_message_begin()
        on_header(name: bytes, value: bytes)
        on_header_complete()
        on_body(body: bytes)
        on_message_complete()
        on_chunk_header()
        on_chunk_complete()
        :param message:
        """
        self._message = message
        self._http_version: bytes = None
        self._keep_alive: bool = None
        self._max_initial_length: int = 8 * 1024  # 8K
        self._max_body_length: int = 52428800  # 50M
        self._buffer_data = bytearray()  # 备份传入数据

    def feed_data(self, data: bytes) -> None:
        """
        解析传入数据，最终触发 HttpMessage协议的回调对象，http升级时，此方法将触发 HttpParserUpgrade 异常
        :param data:
        :return:
        """
        if not data:
            return  # 没有数据传入，所以什么都不做。
        self._buffer_data += data

        basic_info, origin_headers = self._parse_initial().split(b'\r\n', 1)  # 分割抱头为起始行和头部
        self._parse_line(basic_info)
        self._headers_parse(origin_headers)
        if self._buffer_data and len(self._buffer_data) < self._max_body_length:
            self._message.on_body(self._buffer_data)
        self._message.on_message_complete()
        del self._buffer_data[:len(self._buffer_data)]

    def _parse_initial(self) -> bytes:
        # 查找空行 \r\n\r\n 位置长度
        _initial_end = self._buffer_data.find(b'\r\n\r\n')

        if _initial_end == -1:
            if len(self._buffer_data) > self._max_initial_length:
                #  初始信息过大
                raise EntityTooLarge("Initial Exceed its Maximum Length.")

        # 加上换行 \r\n 长度
        _initial_end = _initial_end + 2
        if _initial_end > self._max_initial_length:
            raise EntityTooLarge("Initial Exceed its Maximum length.")

        _pending_initial = ensure_bytes(self._buffer_data[:_initial_end])

        del self._buffer_data[:_initial_end + 2]  # 删除头部

        return _pending_initial

    def _headers_parse(self, data: bytes) -> None:
        """
        解析头信息
        :param data:
        :return:
        """
        _header = {}
        _headers_lines = data.split(b'\r\n')

        for header in _headers_lines:
            if not header:
                continue
            _name, _value = header.split(b':', 1)
            _name, _value = _name.strip(), _value.strip()
            _header[_name] = _value
            self._message.on_header(_name, _value)

        if _header.get(b'Connection', None) == b'keep-alive':
            self._keep_alive = True
        else:
            self._keep_alive = False

        self._message.on_headers_complete()

        if _header.get(b"Upgrade", None):
            raise HttpParserUpgrade('Connection protocols need to be upgraded')

        _header.clear()

    def get_http_version(self) -> str:
        """
        返回 http 协议版本
        :return: str
        """
        if self._http_version:
            return self._http_version.decode('utf-8')
        else:
            return ''

    def should_keep_alive(self) -> bool:
        """
        如果Keep_Alive持久连接是首选，则返回 True
        :return: bool
        """
        return self._keep_alive

    @abc.abstractmethod
    def _parse_line(self, basic: bytes) -> None:
        """
        起始行解析
        :param basic: 报头第一行数据
        :return:
        """
        pass


class HttpRequestParser(AbstractHttpParser):
    def __init__(self, message: HttpMessage):
        self._method: bytes = None
        self._origin_path: bytes = None
        super().__init__(message)

    def _parse_line(self, basic: bytes) -> None:
        """
        起始行解析
        """
        _basic_info = basic.split(b' ')  # 分割起始行
        if len(_basic_info) != 3:
            raise InvalidMessage("Bad Initial Received.")
        self._method, self._origin_path, self._http_version = _basic_info

    def get_method(self) -> bytes:
        """
        返回 http 请求方法(GET, POST, HEAD 等)
        此方法只适用于 HttpRequest
        :return: bytes
        """
        return self._method


class HttpResponseParser(AbstractHttpParser):
    def __init__(self, message: HttpMessage):
        self._status_code: int = None
        self._reason_phrase: bytes = None
        super().__init__(message)

    def _parse_line(self, basic: bytes) -> None:
        _basic_info = basic.split(b' ')  # 分割起始行
        if len(_basic_info) != 3:
            raise InvalidMessage("Bad Initial Received.")
        self._http_version, self._status_code, self._reason_phrase = _basic_info

    def get_status_code(self) -> int:
        """
        返回 http 响应的状态码
        此方法只适用于 HttpResponse
        :return: int
        """
        return self._status_code