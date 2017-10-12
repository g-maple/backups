import struct
import sys
from .primitives import *
from .errors import *
from ..abc import AbstractMessageParser

__all__ = [
    "Http2Parser"
]
_BYTE_ORDER = sys.byteorder
_PARSER_STATE_EMPTY = 0
_PARSER_STATE_LENGTH = 1
_PARSER_STATE_MESSAGE_TYPE = 2
_PARSER_STATE_FLAGS = 3
_PARSER_STATE_STREAM = 4
_PARSER_STATE_PAYLOAD = 5
_FRAME_TYPES_REQUIRE_STREAM_ID = {
    FRAME_TYPE_DATA,
    FRAME_TYPE_RST_STREAM,
    FRAME_TYPE_PRIORITY,
    FRAME_TYPE_PUSH_PROMISE
}
_FRAME_TYPES_REQUIRE_NO_STREAM_ID = {
    FRAME_TYPE_SETTINGS,
    FRAME_TYPE_PING,
    FRAME_TYPE_GO_AWAY
}


def _grouper(sequence, size):
    return [sequence[pos:pos+size] for pos in range(0, len(sequence), size)]


class Http2Parser(AbstractMessageParser):
    def __init__(self):
        self._state = _PARSER_STATE_EMPTY
        self._length = 0
        self._buffer = b''
        AbstractMessageParser.__init__(self)

    def _reset(self):
        self._state = _PARSER_STATE_EMPTY
        self.message = None

    def set_target(self, message: Http2Frame):
        pass

    def feed_data(self, data: bytes):
        self._buffer += data
        buffer_length = len(self._buffer)
        buffer_offset = 0

        if self._state == _PARSER_STATE_EMPTY and buffer_length > 2:
            self._length = int.from_bytes(self._buffer[:3], "big")
            self._state = _PARSER_STATE_LENGTH
            buffer_length -= 3
            buffer_offset += 3

        if self._state == _PARSER_STATE_LENGTH and buffer_length > 0:
            frame_type = self._buffer[buffer_offset]
            if frame_type == FRAME_TYPE_DATA:
                self.message = Http2DataFrame()

            elif frame_type == FRAME_TYPE_HEADERS:
                self.message = Http2HeadersFrame()

            elif frame_type == FRAME_TYPE_PRIORITY:
                self.message = Http2PriorityFrame()

            elif frame_type == FRAME_TYPE_RST_STREAM:
                if self._length != 4:
                    raise Http2ConnectionError(ERROR_CODE_FRAME_SIZE_ERROR)
                self.message = Http2RstStreamFrame()

            elif frame_type == FRAME_TYPE_SETTINGS:
                if self._length % 6:
                    raise Http2ConnectionError(ERROR_CODE_FRAME_SIZE_ERROR)
                self.message = Http2SettingsFrame()

            elif frame_type == FRAME_TYPE_PUSH_PROMISE:
                self.message = Http2PushPromiseFrame()

            elif frame_type == FRAME_TYPE_PING:
                if self._length != 8:
                    raise Http2ConnectionError(ERROR_CODE_FRAME_SIZE_ERROR)
                self.message = Http2PingFrame()

            elif frame_type == FRAME_TYPE_GO_AWAY:
                self.message = Http2GoAwayFrame()

            elif frame_type == FRAME_TYPE_WINDOW_UPDATE:
                self.message = Http2WindowUpdateFrame()

            elif frame_type == FRAME_TYPE_CONTINUATION:
                self.message = Http2ContinuationFrame()

            else:
                self.message = Http2Frame(frame_type)

            buffer_offset += 1
            buffer_length -= 1
            self._state = _PARSER_STATE_FLAGS

        if self._state == _PARSER_STATE_FLAGS and buffer_length > 0:
            self.message.frame_flags = self._buffer[buffer_offset]
            buffer_offset += 1
            buffer_length -= 1
            self._state = _PARSER_STATE_STREAM

            if self.message.frame_type == FRAME_TYPE_SETTINGS and self.message.frame_flags & 0x1 and self._length:
                raise Http2ConnectionError(ERROR_CODE_FRAME_SIZE_ERROR)

        if self._state == _PARSER_STATE_STREAM and buffer_length > 3:
            self.message.stream_id = int.from_bytes(self._buffer[buffer_offset:buffer_offset + 4], "big") & 0x7FFFFFFF
            buffer_offset += 4
            buffer_length -= 4
            self._state = _PARSER_STATE_PAYLOAD

            # These frame types require a non-zero stream_id.
            if self.message.stream_id == 0:
                if self.message.frame_type in _FRAME_TYPES_REQUIRE_STREAM_ID:
                    raise Http2ConnectionError(ERROR_CODE_PROTOCOL_ERROR)

            # These frame types require a stream_id of 0.
            elif self.message.frame_type in _FRAME_TYPES_REQUIRE_NO_STREAM_ID:
                raise Http2ConnectionError(ERROR_CODE_PROTOCOL_ERROR)

            if self.message.frame_type == FRAME_TYPE_PRIORITY:
                if self._length != 5:
                    raise Http2StreamError(self.message.stream_id, ERROR_CODE_FRAME_SIZE_ERROR)

        if self._state == _PARSER_STATE_PAYLOAD and buffer_length >= self._length:
            if isinstance(self.message, Http2PaddedFrame) and self.message.padded:
                padding_length = self._buffer[buffer_offset]
                if padding_length == 0:
                    padding_length = 1
                buffer_offset += 1
            else:
                padding_length = 0

            if self.message.frame_type == FRAME_TYPE_DATA:
                payload_length = self._length - padding_length - (1 if padding_length else 0)
                self.message.payload = self._buffer[buffer_offset:buffer_offset + payload_length]
                buffer_offset += payload_length

            elif self.message.frame_type == FRAME_TYPE_HEADERS:
                if self.message.priority:
                    dependent_stream_id = struct.unpack(">I", self._buffer[buffer_offset:buffer_offset + 4])[0]
                    self.message.exclusive = True if dependent_stream_id & 0x80000000 else False
                    self.message.dependent_stream_id = dependent_stream_id & 0x7FFFFFFF
                    self.message.weight = self._buffer[buffer_offset + 4] + 1
                    buffer_offset += 5

                payload_length = self._length - (5 if self.message.priority else 0) - padding_length - (1 if padding_length else 0)
                self.message.payload = self._buffer[buffer_offset:buffer_offset + payload_length]
                buffer_offset += payload_length

            elif self.message.frame_type == FRAME_TYPE_PRIORITY:
                dependent_stream_id = struct.unpack(">I", self._buffer[buffer_offset:buffer_offset + 4])[0]
                self.message.exclusive = True if dependent_stream_id & 0x80000000 else False
                self.message.dependent_stream_id = dependent_stream_id & 0x7FFFFFFF
                self.message.weight = self._buffer[buffer_offset + 4] + 1
                buffer_offset += 5

            elif self.message.frame_type == FRAME_TYPE_RST_STREAM:
                self.message.error_code = int.from_bytes(self._buffer[buffer_offset:buffer_offset + 4], "big")
                buffer_offset += 4

            elif self.message.frame_type == FRAME_TYPE_SETTINGS:
                settings = struct.unpack(">" + ("HI" * (self._length // 6)), self._buffer[buffer_offset:buffer_offset + self._length])
                for settings_key, settings_value in _grouper(settings, 2):
                    self.message.settings[settings_key] = settings_value
                buffer_offset += self._length

            elif self.message.frame_type == FRAME_TYPE_PUSH_PROMISE:
                self.message.promised_stream_id = int.from_bytes(self._buffer[buffer_offset:buffer_offset + 4], "big") & 0x7FFFFFFF
                payload_length = self._length - padding_length - (1 if padding_length else 0)
                self.message.payload = self._buffer[buffer_offset + 4:buffer_offset + payload_length]
                buffer_offset += payload_length

            elif self.message.frame_type == FRAME_TYPE_PING:
                self.message.payload = self._buffer[buffer_offset:buffer_offset + 8]
                buffer_offset += 8

            elif self.message.frame_type == FRAME_TYPE_GO_AWAY:
                self.message.last_stream_id = int.from_bytes(self._buffer[buffer_offset:buffer_offset + 4], "big") & 0x7FFFFFFF
                self.message.error_code = int.from_bytes(self._buffer[buffer_offset + 4:buffer_offset + 8], "big")
                self.message.payload = self._buffer[buffer_offset + 8:self._length]
                buffer_offset += self._length

            elif self.message.frame_type == FRAME_TYPE_WINDOW_UPDATE:
                self.message.window_size = int.from_bytes(self._buffer[buffer_offset:buffer_offset + 4], "big") & 0x7FFFFFFF
                buffer_offset += 4

            elif self.message.frame_type == FRAME_TYPE_CONTINUATION:
                self.message.payload = self._buffer[buffer_offset:buffer_offset + self._length]
                buffer_offset += self._length

            if padding_length > 0:
                self.message.padding = self._buffer[buffer_offset:buffer_offset + padding_length]
                buffer_offset += padding_length

            self.message.on_complete()

        self._buffer = self._buffer[buffer_offset:]
