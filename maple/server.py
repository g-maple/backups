import asyncio
import os
from typing import Optional
from .protocol.http.protocol import HttpProtocol
import ssl

__all__ = [
    "Server"
]


class _BaseWebProtocol(asyncio.Protocol):
    """
    服务器socket监听数据中转，方便客户端不同请求协议切换
    """
    def __init__(self, server):
        self.server = server
        self.protocol = None
        self._connection_timeout = None
        self.loop: asyncio.AbstractEventLoop = server.loop
        super().__init__()

    def connection_made(self, transport: asyncio.WriteTransport):
        if self.protocol is None:
            self.protocol = self.server.default_protocol(self)
        self.protocol.open(transport)
        self._reset_connection_timeout()

    def data_received(self, data: bytes):
        self.protocol.receive_data(data)

    def connection_lost(self, exc):
        self.protocol.close(exc)

    def _reset_connection_timeout(self, timeout: int=5):
        self._cancle_connection_timeout()
        self._connection_timeout = self.loop.call_later(
            timeout, self._connection_timeout_close
        )

    def _cancle_connection_timeout(self):
        if self._connection_timeout:
            self._connection_timeout.cancel()
        self._connection_timeout = None

    def _connection_timeout_close(self):
        print('\033[35m 连接超时\033[0m')

        self._connection_close()

    def _connection_close(self):
        self._cancle_connection_timeout()
        self.protocol._transport.close()


class Server:
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop]=None, *, debug: bool=False):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self._debug = debug
        self.default_protocol = HttpProtocol

    def run(self, host: str="127.0.0.1", port: int=8080, _ssl: ssl.SSLContext=None):
        print("\033[31m ===== Running on {}://{}:{}/ (Maple/0.1) =====\n(Press Ctrl+C to quit)\033[0m".format(
            "http" if _ssl is None else "https",
            host, port
        ))

        try:
            http_server = self.loop.run_until_complete(self.loop.create_server(lambda: _BaseWebProtocol(self), host, port, ssl=_ssl))
        except:
            print("Unable to start server")
            return

        pid = os.getpid()
        try:
            print("\033[32m Starting worker [{}] \033[0m".format(pid))
            self.loop.run_forever()
        except KeyboardInterrupt:
            print("\033[33m Ready to quit service \033[0m")
        finally:
            print("\033[31m Stopping worker [{}] \033[0m".format(pid))
            http_server.close()
            self.loop.run_until_complete(http_server.wait_closed())
            self.loop.close()
