import abc
from .parser import *
from .primitives import *
from ..abc import AbstractWebProtocol

__all__ = [
    "AbstractWebSocketProtocol",
    "SUPPORTED_WEBSOCKET_VERSIONS",
    "WEBSOCKET_SECRET_KEY"
]
SUPPORTED_WEBSOCKET_VERSIONS = {b'13', b'8', b'7'}
WEBSOCKET_SECRET_KEY = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


class AbstractWebSocketProtocol(AbstractWebProtocol):
    def __init__(self, base):
        self.server = base.server
        self._message = None
        self._parser = WebSocketParser()
        self._sent_close = False
        AbstractWebProtocol.__init__(self, base)

    @abc.abstractmethod
    def receive_message(self, message: WebSocketMessage):
        pass

    def data_received(self, data):
        if self._message is None:
            self._message = WebSocketMessage()
            self._parser.set_target(self._message)
        try:
            self._parser.feed_data(data)
        except WebSocketError as error:
            self.close(error.close_code)

        if self._message.is_complete():

            # Response to PING messages with a PONG.
            if self._message.message_code == MESSAGE_CODE_PING:
                self._transport.write(WebSocketMessage(message_code=MESSAGE_CODE_PONG, payload=self._message.payload).to_bytes())

            # Unsolicited PONG message should be ignored.
            elif self._message.message_code == MESSAGE_CODE_PONG:
                pass

            elif self._message.message_code == MESSAGE_CODE_CLOSE:
                # If our Transport is already closing, then it must have been us that initiated.
                self.close()

            # If our Transport is closing, then don't send any more messages.
            elif not self._transport.is_closing():
                self.receive_message(self._message)

            self._message = None

    def send_message(self, message: WebSocketMessage):
        self._transport.write(message.to_bytes())

    def close(self, close_code: int=CLOSE_CODE_PROTOCOL_ERROR):
        if not self._transport.is_closing():
            if not self._sent_close:
                self._sent_close = True
                self._transport.write(WebSocketMessage(message_code=MESSAGE_CODE_CLOSE, close_code=close_code))
            self._transport.close()
