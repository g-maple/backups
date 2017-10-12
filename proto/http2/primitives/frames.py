import os
import struct
import typing
from .hpack import HeaderBlockFragment
from ...abc import AbstractMessage

__all__ = [
    "Http2Frame",
    "Http2PaddedFrame",
    "Http2DataFrame",
    "Http2HeadersFrame",
    "Http2PriorityFrame",
    "Http2RstStreamFrame",
    "Http2SettingsFrame",
    "Http2PushPromiseFrame",
    "Http2PingFrame",
    "Http2GoAwayFrame",
    "Http2WindowUpdateFrame",
    "Http2ContinuationFrame",

    "ERROR_CODE_NO_ERROR",
    "ERROR_CODE_PROTOCOL_ERROR",
    "ERROR_CODE_INTERNAL_ERROR",
    "ERROR_CODE_FLOW_CONTROL_ERROR",
    "ERROR_CODE_SETTINGS_TIMEOUT",
    "ERROR_CODE_STREAM_CLOSED",
    "ERROR_CODE_FRAME_SIZE_ERROR",
    "ERROR_CODE_REFUSED_STREAM",
    "ERROR_CODE_CANCEL",
    "ERROR_CODE_COMPRESSION_ERROR",
    "ERROR_CODE_CONNECT_ERROR",
    "ERROR_CODE_ENHANCE_YOUR_CALM",
    "ERROR_CODE_INADEQUATE_SECURITY",
    "ERROR_CODE_HTTP_1_1_REQUIRED",

    "FRAME_TYPE_DATA",
    "FRAME_TYPE_HEADERS",
    "FRAME_TYPE_PRIORITY",
    "FRAME_TYPE_RST_STREAM",
    "FRAME_TYPE_SETTINGS",
    "FRAME_TYPE_PUSH_PROMISE",
    "FRAME_TYPE_PING",
    "FRAME_TYPE_GO_AWAY",
    "FRAME_TYPE_WINDOW_UPDATE",
    "FRAME_TYPE_CONTINUATION",

    "SETTINGS_HEADER_TABLE_SIZE",
    "SETTINGS_ENABLE_PUSH",
    "SETTINGS_MAX_CONCURRENT_STREAMS",
    "SETTINGS_INITIAL_WINDOW_SIZE",
    "SETTINGS_MAX_FRAME_SIZE",
    "SETTINGS_MAX_HEADER_LIST_SIZE"
]

ERROR_CODE_NO_ERROR = 0x0
ERROR_CODE_PROTOCOL_ERROR = 0x1
ERROR_CODE_INTERNAL_ERROR = 0x2
ERROR_CODE_FLOW_CONTROL_ERROR = 0x3
ERROR_CODE_SETTINGS_TIMEOUT = 0x4
ERROR_CODE_STREAM_CLOSED = 0x5
ERROR_CODE_FRAME_SIZE_ERROR = 0x6
ERROR_CODE_REFUSED_STREAM = 0x7
ERROR_CODE_CANCEL = 0x8
ERROR_CODE_COMPRESSION_ERROR = 0x9
ERROR_CODE_CONNECT_ERROR = 0xA
ERROR_CODE_ENHANCE_YOUR_CALM = 0xB
ERROR_CODE_INADEQUATE_SECURITY = 0xC
ERROR_CODE_HTTP_1_1_REQUIRED = 0xD

FRAME_TYPE_DATA = 0x0
FRAME_TYPE_HEADERS = 0x1
FRAME_TYPE_PRIORITY = 0x2
FRAME_TYPE_RST_STREAM = 0x3
FRAME_TYPE_SETTINGS = 0x4
FRAME_TYPE_PUSH_PROMISE = 0x5
FRAME_TYPE_PING = 0x6
FRAME_TYPE_GO_AWAY = 0x7
FRAME_TYPE_WINDOW_UPDATE = 0x8
FRAME_TYPE_CONTINUATION = 0x9

SETTINGS_HEADER_TABLE_SIZE = 0x1
SETTINGS_ENABLE_PUSH = 0x2
SETTINGS_MAX_CONCURRENT_STREAMS = 0x3
SETTINGS_INITIAL_WINDOW_SIZE = 0x4
SETTINGS_MAX_FRAME_SIZE = 0x5
SETTINGS_MAX_HEADER_LIST_SIZE = 0x6


class Http2Frame(AbstractMessage):
    def __init__(self, frame_type: int):
        self.frame_type = frame_type
        self.frame_flags = 0x0
        self.stream_id = 0
        self.payload = b''
        self.is_padded = False
        self.is_flow_controlled = False
        self._is_complete = False
        AbstractMessage.__init__(self)

    def on_complete(self):
        self._is_complete = True

    def is_complete(self):
        return self._is_complete

    def to_bytes(self) -> bytes:
        return len(self.payload).to_bytes(3, "big") + \
               struct.pack(
                   ">BBI",
                   self.frame_type,
                   self.frame_flags,
                   self.stream_id & 0x7FFFFFFF
               ) + self.payload


class Http2PaddedFrame(Http2Frame):
    def __init__(self, frame_type: int):
        self._payload = b''
        self._padding = b''
        Http2Frame.__init__(self, frame_type)

    def random_padding(self):
        self.padding = b'\x00' * os.urandom(1)[0]
        self.padded = True

    @property
    def padding(self) -> bytes:
        return self._padding if len(self._padding) else (b'\x00' if self.padded else b'')

    @padding.setter
    def padding(self, padding: bytes):
        if padding:
            if len(padding) > 0xFF:
                raise ValueError("HTTP/2 frame padding cannot be longer than 255 bytes.")
            self._padding = padding
            self.padded = True
        else:
            self._padding = b''
            self.padded = False

    @property
    def padded(self) -> bool:
        return True if self.frame_flags & 0x08 else False

    @padded.setter
    def padded(self, padded: bool):
        if padded:
            self.frame_flags |= 0x08
        else:
            self.frame_flags &= 0xF7

    def to_bytes(self):
        payload = b''
        padding = self._padding
        if self.padded:
            if len(padding) == 0:
                padding = b'\x00'
            payload += struct.pack(">B", len(self._padding))
        payload += self.payload
        payload += padding
        return len(payload).to_bytes(3, "big") + \
               struct.pack(
                   ">BBI",
                   self.frame_type,
                   self.frame_flags,
                   self.stream_id & 0x7FFFFFFF
               ) + payload


class Http2DataFrame(Http2PaddedFrame):
    def __init__(self):
        Http2PaddedFrame.__init__(self, FRAME_TYPE_DATA)
        self.is_flow_controlled = True

    @property
    def end_stream(self) -> bool:
        return True if self.frame_flags & 0x01 else False

    @end_stream.setter
    def end_stream(self, end_stream: bool):
        if end_stream:
            self.frame_flags |= 0x01
        else:
            self.frame_flags &= 0x7F


class Http2HeadersFrame(Http2PaddedFrame):
    def __init__(self):
        self.dependent_stream_id = 0
        self.weight = 16
        self.exclusive = False
        Http2PaddedFrame.__init__(self, FRAME_TYPE_HEADERS)

    @property
    def end_stream(self) -> bool:
        return True if self.frame_flags & 0x01 else False

    @end_stream.setter
    def end_stream(self, end_stream: bool):
        if end_stream:
            self.frame_flags |= 0x01
        else:
            self.frame_flags &= 0xFE

    @property
    def end_headers(self) -> bool:
        return True if self.frame_flags & 0x04 else False

    @end_headers.setter
    def end_headers(self, end_headers: bool):
        if end_headers:
            self.frame_flags |= 0x04
        else:
            self.frame_flags &= 0xFB

    @property
    def priority(self):
        return True if self.frame_flags & 0x20 else False

    @priority.setter
    def priority(self, priority):
        if priority:
            self.frame_flags |= 0x20
        else:
            self.frame_flags &= 0xDF

    def to_bytes(self):
        payload = b''
        padding = self._padding
        if self.padded:
            if len(padding) == 0:
                padding = b'\x00'
            payload += struct.pack(">B", len(self._padding))
        if self.priority:
            payload += struct.pack(
                ">IB",
                (0x80000000 if self.exclusive else 0) | (self.dependent_stream_id & 0x7FFFFFFF),
                (self.weight - 1) & 0xFF
            )
        payload += self.payload
        payload += padding
        return len(payload).to_bytes(3, "big") + \
               struct.pack(
                   ">BBI",
                   self.frame_type,
                   self.frame_flags,
                   self.stream_id & 0x7FFFFFFF
               ) + payload


class Http2PriorityFrame(Http2Frame):
    def __init__(self):
        self.dependent_stream_id = 0
        self.exclusive = False
        self.weight = 16
        Http2Frame.__init__(self, FRAME_TYPE_PRIORITY)

    def to_bytes(self) -> bytes:
        return (5).to_bytes(3, "big") + \
               struct.pack(
                   ">BBIIB",
                   self.frame_type,
                   self.frame_flags,
                   self.stream_id,
                   (0x80000000 if self.exclusive else 0) | (self.dependent_stream_id & 0x7FFFFFFF),
                   (self.weight - 1) & 0xFF
               )


class Http2RstStreamFrame(Http2Frame):
    def __init__(self):
        self.error_code = 0
        Http2Frame.__init__(self, FRAME_TYPE_RST_STREAM)

    def to_bytes(self) -> bytes:
        return (4).to_bytes(3, "big") + \
               struct.pack(
                   ">BBII",
                   self.frame_type,
                   self.frame_flags,
                   self.stream_id & 0x7FFFFFFF,
                   self.error_code & 0xFFFFFFFF
               )


class Http2SettingsFrame(Http2Frame):
    def __init__(self):
        self.settings = {}  # type: typing.Dict[int, int]
        Http2Frame.__init__(self, FRAME_TYPE_SETTINGS)

    def to_bytes(self) -> bytes:
        return (len(self.settings) * 6).to_bytes(3, "big") + \
               struct.pack(
                   ">BBI",
                   self.frame_type,
                   self.frame_flags,
                   self.stream_id & 0x7FFFFFFF,
               ) + b''.join([struct.pack(">HI", key, value) for key, value in self.settings.items()])


class Http2PushPromiseFrame(Http2PaddedFrame):
    def __init__(self):
        self.promised_stream_id = 0
        Http2PaddedFrame.__init__(self, FRAME_TYPE_PUSH_PROMISE)

    def to_bytes(self):
        payload = b''
        padding = self._padding
        if self.padded:
            if len(padding) == 0:
                padding = b'\x00'
            payload += struct.pack(">B", len(self._padding))
        payload += struct.pack(">I", self.promised_stream_id & 0x7FFFFFFF)
        payload += self.payload
        payload += padding
        return len(payload).to_bytes(3, "big") + \
               struct.pack(
                   ">BBI",
                   self.frame_type,
                   self.frame_flags,
                   self.stream_id & 0x7FFFFFFF
               ) + payload


class Http2PingFrame(Http2Frame):
    def __init__(self):
        Http2Frame.__init__(self, FRAME_TYPE_PING)

    @property
    def ack(self) -> bool:
        return True if self.frame_flags & 0x1 else False

    @ack.setter
    def ack(self, ack: bool):
        if ack:
            self.frame_flags |= 0x1
        else:
            self.frame_flags &= 0xFE

    def random_payload(self):
        self.payload = os.urandom(8)

    def to_bytes(self):
        return len(self.payload).to_bytes(3, "big") + \
               struct.pack(
                   ">BBI",
                   self.frame_type,
                   self.frame_flags,
                   self.stream_id & 0x7FFFFFFF
               ) + self.payload


class Http2GoAwayFrame(Http2Frame):
    def __init__(self):
        self.last_stream_id = 0
        self.error_code = 0
        Http2Frame.__init__(self, FRAME_TYPE_GO_AWAY)

    def to_bytes(self):
        return (len(self.payload) + 8).to_bytes(3, "big") + \
               struct.pack(
                   ">BBIII",
                   self.frame_type,
                   self.frame_flags,
                   self.stream_id & 0x7FFFFFFF,
                   self.last_stream_id & 0x7FFFFFFF,
                   self.error_code & 0xFFFFFFFF
               ) + self.payload


class Http2WindowUpdateFrame(Http2Frame):
    def __init__(self):
        self.window_size = 0
        Http2Frame.__init__(self, FRAME_TYPE_WINDOW_UPDATE)

    def to_bytes(self):
        return (4).to_bytes(3, "big") + \
               struct.pack(
                   ">BBII",
                   self.frame_type,
                   self.frame_flags,
                   self.stream_id & 0x7FFFFFFF,
                   self.window_size & 0x7FFFFFFF
               )


class Http2ContinuationFrame(Http2Frame):
    def __init__(self):
        Http2Frame.__init__(self, FRAME_TYPE_CONTINUATION)

    @property
    def end_headers(self) -> bool:
        return True if self.frame_flags & 0x04 else False

    @end_headers.setter
    def end_headers(self, end_headers: bool):
        if end_headers:
            self.frame_flags |= 0x04
        else:
            self.frame_flags &= 0xFB
