import base64
import hashlib
import datetime
import httptools
from .primitives import *
from .parser import HttpParser
from ..abc import AbstractWebProtocol, AbstractMessage
from ..websockets import SUPPORTED_WEBSOCKET_VERSIONS, WEBSOCKET_SECRET_KEY, AbstractWebSocketProtocol

__all__ = [
    "HttpProtocol"
]


class HttpProtocol(AbstractWebProtocol):
    def __init__(self, base):
        self.server = base.server
        self._version = None
        self._request = HttpRequest()
        self._parser = HttpParser(self._request)
        AbstractWebProtocol.__init__(self, base)

    def receive_message(self, message: AbstractMessage):
        self.loop.create_task(self.server.http_handler(self, message))

    def receive_data(self, data: bytes):
        if self._request is None:
            self._request = HttpRequest()
            self._parser.set_target(self._request)

        try:
            self._parser.feed_data(data)

        # If we receive the Upgrade, then attempt to process the Upgrade otherwise process request normally.
        except httptools.HttpParserUpgrade:
            upgrade_protocols = self._request.header.qlist(b'Upgrade')
            if b'websocket' in upgrade_protocols and \
               self._request.headers.get(b'Sec-WebSocket-Version', [b''])[0] in SUPPORTED_WEBSOCKET_VERSIONS:

                # If the server_origins has entries, then check Origin header.
                if self.server.server_origins:
                    bad_origin = False
                    if b'Origin' not in self._request.headers:
                        bad_origin = True
                    else:
                        for entry, _ in self._request.headers.qlist(b'Origin'):
                            if entry in self.server.server_origins:
                                break
                        else:
                            bad_origin = True
                    if bad_origin:
                        response = HttpResponse(
                            status_code=403,
                            status=b'Forbidden',
                            headers={
                                b'Date': datetime.datetime.utcnow(),
                                b'Server': self.server.server_header
                            }
                        )
                        response.version = self._request.version
                        self._transport.write(response.to_bytes())
                        return

                # Calculate the combined Sec-WebSocket-Key and GUID for the Sec-WebSocket-Accept key.
                websocket_combine_key = self._request.headers[b'Sec-WebSocket-Key'][0] + WEBSOCKET_SECRET_KEY
                websocket_accept_key = base64.b64encode(hashlib.sha1(websocket_combine_key).digest())

                upgrade_response = HttpResponse(
                    status_code=101,
                    status=b'Switching Protocols',
                    headers={
                        b'Connection': b'Upgrade',
                        b'Upgrade': b'websocket',
                        b'Sec-WebSocket-Accept': websocket_accept_key,
                        b'Date': datetime.datetime.utcnow(),
                        b'Server': self.server.server_header
                    }
                )

                # HTTP version is not parsed before the HttpParserUpgrade exception is thrown. Must
                upgrade_response.version = self._version if self._version is not None else b'1.1'
                self._transport.write(upgrade_response.to_bytes())
                self.switch_protocol(AbstractWebSocketProtocol(self.base.server))
                return

        if self._request.is_complete():
            if self._version is None:
                self._version = self._request.version
            self.receive_message(self._request)
            self._request = None

    def send_message(self, message: AbstractMessage):
        self._transport.write(message.to_bytes())