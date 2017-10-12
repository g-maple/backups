import abc
import asyncio
import types
import typing
import ssl

__all__ = [
    "_BaseWebProtocol",
    "AbstractMessage",
    "AbstractMessageParser",
    "AbstractWebProtocol"
]
_HAS_NPN = ssl.HAS_NPN
_HAS_ALPN = ssl.HAS_ALPN


class _BaseWebProtocol(asyncio.Protocol):
    def __init__(self, server):
        self.server = server
        self.protocol = None
        self.loop = server.loop

    def connection_made(self, transport: asyncio.WriteTransport):
        ssl_context = transport.get_extra_info("ssl_object")
        if ssl_context is not None and hasattr(ssl_context, "selected_alpn_protocol"):
            if _HAS_ALPN:
                alpn_protocol = ssl_context.selected_alpn_protocol()
                if alpn_protocol is not None:
                    self.protocol = self.server.protocols.get(
                        alpn_protocol,
                        self.server.protocols[self.server.default_protocol]
                    )(self)
            if _HAS_NPN and self.protocol is None and hasattr(ssl_context, "selected_npn_protocol"):
                npn_protocol = ssl_context.selected_npn_protocol()
                if npn_protocol is not None:
                    self.protocol = self.server.protocols.get(
                        npn_protocol,
                        self.server.protocols[self.server.default_protocol]
                    )(self)
        if self.protocol is None:
            self.protocol = self.server.protocols[self.server.default_protocol](self)
        self.protocol.open(transport)

    def data_received(self, data):
        self.protocol.receive_data(data)

    def connection_lost(self, exc):
        self.protocol.close(exc)


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
    def __init__(self, base: _BaseWebProtocol):
        self.base = base
        self.loop = self.base.loop  # type: asyncio.AbstractEventLoop
        self._transport = None  # type: asyncio.WriteTransport
        self._running = True

    def switch_protocol(self, protocol):
        self.base.protocol = protocol(self.base)

    def open(self, transport: asyncio.Transport):
        self._transport = transport

    @abc.abstractmethod
    def receive_data(self, data: bytes):
        pass

        # Template for a ServerProtocol.data_received()
        # ---------------------------------------------
        # if self._message is None:
        #     self._message = self._message_type()
        #     self._parser.set_target(self._message)
        # self._parser.feed_data(data)
        # if self._message.is_complete():
        #     self.loop.create_task(self._handler(self._message, self._transport))
        # self._message = None

    @abc.abstractmethod
    def send_message(self, message: AbstractMessage):
        pass

    @abc.abstractmethod
    def receive_message(self, message: AbstractMessage):
        pass

    def close(self, exc=None):
        self._transport.close()
        self._transport = None
        self._running = False
