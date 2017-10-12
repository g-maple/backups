import sys
import struct
from .primitives import *
from ..abc import AbstractMessageParser

__all__ = [
    "WebSocketError",
    "WebSocketParser"
]
_BYTE_ORDER = sys.byteorder
_PARSER_STATE_EMPTY = 0
_PARSER_STATE_HEADER = 1
_PARSER_STATE_GET_LENGTH = 2
_PARSER_STATE_MASK = 3
_PARSER_STATE_PAYLOAD = 4
_MAX_MESSAGE_LENGTH = (1024 * 1024)


class WebSocketError(Exception):
    def __init__(self, close_code: int, *args, **kwargs):
        self.close_code = close_code
        Exception.__init__(self, *args, **kwargs)


class WebSocketParser(AbstractMessageParser):
    def __init__(self, message: WebSocketMessage=None):
        self._buffer = bytearray()
        self._state = _PARSER_STATE_EMPTY
        self._length = 0
        self._masked = 0
        self._mask = 0
        self._frame = WebSocketFrame()
        AbstractMessageParser.__init__(self, message)

    def _reset(self):
        self._state = _PARSER_STATE_EMPTY
        self._masked = 0
        self._frame = WebSocketFrame()

    def set_target(self, message: WebSocketMessage):
        self.message = message

    def feed_data(self, data: bytes):
        self._buffer += data
        buffer_length = len(self._buffer)

        # Parsing the WebSocketFrame header (2 bytes)
        if self._state == _PARSER_STATE_EMPTY and buffer_length > 1:

            first_byte, second_byte = self._buffer[:2]
            reserved = first_byte & 0x70
            if reserved:
                raise WebSocketError(CLOSE_CODE_PROTOCOL_ERROR, "Received frame with non-zero reserved bits.")

            last_frame = first_byte & 0x80
            message_code = first_byte & 0x7F

            if message_code > 7 and not last_frame:
                raise WebSocketError(CLOSE_CODE_PROTOCOL_ERROR, "Received fragmented control frame.")

            self._masked = second_byte & 0x80
            self._length = second_byte & 0x7F

            if message_code > 7 and self._length > 125:
                raise WebSocketError(CLOSE_CODE_PROTOCOL_ERROR, "Received a control frame with length greater than 125 bytes.")

            self._frame.message_code = message_code
            self._frame.last_frame = 1 if last_frame else 0

            self._state = _PARSER_STATE_HEADER if self._length > 125 else (
                _PARSER_STATE_GET_LENGTH if self._masked else _PARSER_STATE_MASK
            )
            self._buffer = self._buffer[2:]
            buffer_length -= 2

        # Parsing the WebSocketFrame length (if needed) (2 or 8 bytes)
        if self._state == _PARSER_STATE_HEADER:
            if self._length == 126 and buffer_length > 1:
                self._length = struct.unpack("=H", self._buffer[:2])
                self._state = _PARSER_STATE_GET_LENGTH
                self._buffer = self._buffer[2:]
                buffer_length -= 2

            elif self._length > 126 and buffer_length > 7:
                self._length = struct.unpack("=Q", self._buffer[:8])[0]
                self._state = _PARSER_STATE_GET_LENGTH
                self._buffer = self._buffer[8:]
                buffer_length -= 8

        # Parsing the WebSocketFrame mask (if needed) (4 bytes)
        if self._state == _PARSER_STATE_GET_LENGTH and buffer_length > 3:
            self._mask = self._buffer[:4]
            self._state = _PARSER_STATE_MASK
            self._buffer = self._buffer[4:]
            buffer_length -= 4

        # Parsing the WebSocketFrame payload (many bytes)
        if self._state == _PARSER_STATE_MASK and buffer_length >= self._length:
            self._frame.payload = bytes(self._buffer[:self._length])
            if self._masked:
                self._frame.payload = (
                    int.from_bytes(self._frame.payload, "big") ^
                    (int.from_bytes(self._mask * (self._length >> 2) + self._mask[:self._length & 3], "big"))
                ).to_bytes(self._length, _BYTE_ORDER)

            # If this is a close message, then get the close code from the payload.
            if self._frame.message_code == MESSAGE_CODE_CLOSE:
                self._frame.close_code = struct.unpack("=H", self._frame.payload[:2])[0]
                self._frame.payload = self._frame.payload[2:]

            self.message.frames.append(self._frame)
            self._buffer = self._buffer[self._length:]

            if len(self.message) > _MAX_MESSAGE_LENGTH:
                raise WebSocketError(CLOSE_CODE_MESSAGE_TOO_BIG, "WebSocketMessage cannot be greater than {} bytes.".format(_MAX_MESSAGE_LENGTH))

            if self._frame.last_frame:
                self.message.on_message_complete()

            self._reset()
