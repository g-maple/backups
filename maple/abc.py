import abc
import asyncio

__all__ = [
    "AbstractMessage",
    "AbstractWebProtocol",
    "AbstractMessageParser"
]


class AbstractMessage(abc.ABC):
    @abc.abstractmethod
    def is_complete(self) -> bool:
        pass

    @abc.abstractmethod
    def to_bytes(self) -> bool:
        pass


class AbstractMessageParser(abc.ABC):
    def __init__(self, message: AbstractMessage=None):
        self.message = None
        if message is not None:
            self.set_target(message)

    @abc.abstractmethod
    def set_target(self, message: AbstractMessage):
        pass

    @abc.abstractmethod
    def feed_data(self, data: bytes):
        pass


class AbstractWebProtocol(abc.ABC):
    def __init__(self, base):
        self.base = base  # server._BaseWebProtocol
        self.loop: asyncio.AbstractEventLoop = self.base.loop
        self._transport: asyncio.WriteTransport = None
        self.sockname = None
        self.peername = None
        self._running = True

    def switch_protocol(self, protocol):
        """
        默认HttpProtocol协议，根据请求需求自动切换协议[WebSocketProtocol]
        :param protocol: AbstractWebProtocol 子类
        :return: None
        """
        self.base.protocol = protocol(self.base)

    def open(self, transport: asyncio.Transport):
        self._transport = transport
        self.sockname = self._transport.get_extra_info("sockname")
        self.peername = self._transport.get_extra_info("peername")
        self.base._reset_connection_timeout()

    @abc.abstractmethod
    def receive_data(self, data: bytes):
        pass

    @abc.abstractmethod
    def send_message(self, meeage: AbstractMessage):
        pass

    @abc.abstractmethod
    def receive_message(self, messag: AbstractMessage):
        pass

    def close(self, exc):
        self.base._connection_close()
        self._transport = None
        self._running = False
