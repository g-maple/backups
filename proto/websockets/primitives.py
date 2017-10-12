import os
import struct
import sys
import typing
from ..abc import AbstractMessage

__all__ = [
    "CLOSE_CODE_PROTOCOL_ERROR",
    "CLOSE_CODE_OK",
    "CLOSE_CODE_GOING_AWAY",
    "CLOSE_CODE_UNSUPPORTED_DATA",
    "CLOSE_CODE_INVALID_TEXT",
    "CLOSE_CODE_POLICY_VIOLATION",
    "CLOSE_CODE_MESSAGE_TOO_BIG",
    "CLOSE_CODE_MANDATORY_EXTENSION",
    "CLOSE_CODE_INTERNAL_ERROR",
    "CLOSE_CODE_SERVICE_RESTART",
    "CLOSE_CODE_TRY_AGAIN_LATER",

    "MESSAGE_CODE_CONTINUE",
    "MESSAGE_CODE_TEXT",
    "MESSAGE_CODE_BINARY",
    "MESSAGE_CODE_CLOSE",
    "MESSAGE_CODE_PING",
    "MESSAGE_CODE_PONG",

    "WebSocketFrame",
    "WebSocketMessage"
]
CLOSE_CODE_OK = 1000
CLOSE_CODE_GOING_AWAY = 1001
CLOSE_CODE_PROTOCOL_ERROR = 1002
CLOSE_CODE_UNSUPPORTED_DATA = 1003
CLOSE_CODE_INVALID_TEXT = 1007
CLOSE_CODE_POLICY_VIOLATION = 1008
CLOSE_CODE_MESSAGE_TOO_BIG = 1009
CLOSE_CODE_MANDATORY_EXTENSION = 1010
CLOSE_CODE_INTERNAL_ERROR = 1011
CLOSE_CODE_SERVICE_RESTART = 1012
CLOSE_CODE_TRY_AGAIN_LATER = 1013

MESSAGE_CODE_CONTINUE = 0
MESSAGE_CODE_TEXT = 1
MESSAGE_CODE_BINARY = 2
MESSAGE_CODE_CLOSE = 8
MESSAGE_CODE_PING = 9
MESSAGE_CODE_PONG = 10

_BYTE_ORDER = sys.byteorder
_MAX_LENGTH_PER_FRAME = 0xFFFFFFFFFFFFFFFF


class WebSocketMessage(AbstractMessage):
    def __init__(self, message_code: int=0, close_code: int=-1, payload: bytes=b''):
        self.message_code = message_code
        self.close_code = close_code
        self.payload = payload
        self.frames = []  # type: typing.List[WebSocketFrame]
        self._is_message_complete = False
        AbstractMessage.__init__(self)

    def __repr__(self):
        return "<WebSocketMessage message_code={} close_code={} payload={}>".format(
            self.message_code, self.close_code, self.payload
        )

    def __len__(self):
        return sum(len(frame) for frame in self.frames)

    def is_complete(self) -> bool:
        return self._is_message_complete

    def on_message_complete(self):
        self._is_message_complete = True
        self.message_code = self.frames[-1].message_code
        self.close_code = self.frames[0].close_code
        self.payload = b''.join([frame.payload for frame in self.frames])

    def to_bytes(self):
        self.to_frames()
        return b''.join([frame.to_bytes() for frame in self.frames])

    def to_frames(self):
        if self.frames:
            self.frames = []
        payload_length = len(self.payload)
        if payload_length > _MAX_LENGTH_PER_FRAME:
            for i in range(len(self.payload) // _MAX_LENGTH_PER_FRAME):
                next_frame = WebSocketFrame(
                    last_frame=0,
                    message_code=MESSAGE_CODE_CONTINUE,
                    payload=self.payload[(i * _MAX_LENGTH_PER_FRAME):((i + 1) * _MAX_LENGTH_PER_FRAME)]
                )
                if i == 0 and self.close_code > 0:
                    next_frame.close_code = self.close_code
                self.frames.append(next_frame)
            payload_length %= _MAX_LENGTH_PER_FRAME
        frames_length = len(self.frames)
        last_frame = WebSocketFrame(
            last_frame=1,
            message_code=self.message_code,
            payload=self.payload[(_MAX_LENGTH_PER_FRAME * frames_length):],
            close_code=self.close_code if self.close_code > 0 and frames_length == 0 else -1
        )
        self.frames.append(last_frame)


class WebSocketFrame:
    def __init__(self, last_frame: int=0, message_code: int=0, payload: bytes=b'', close_code: int=-1):
        self.last_frame = last_frame
        self.message_code = message_code
        self.payload = payload  # type: bytes
        self.close_code = close_code

    def __repr__(self):
        return "<WebSocketFrame message_code={} last_frame={} close_code={} payload={}>".format(
            self.message_code, self.last_frame, self.close_code, self.payload
        )

    def __len__(self):
        return len(self.payload)

    def to_bytes(self) -> bytes:
        length = len(self.payload) + (2 if self.close_code > 0 else 0)

        if length < 126:
            header = struct.pack(">BB", (self.last_frame << 7) | self.message_code, length | 128)
        elif length < 65536:
            header = struct.pack(">BBH", (self.last_frame << 7) | self.message_code, 254, length)
        else:
            header = struct.pack(">BBQ", (self.last_frame << 7) | self.message_code, 255, length)

        mask = struct.pack(">I", struct.unpack("=I", os.urandom(4))[0])
        payload = self.payload
        if self.close_code > 0:
            payload = struct.pack("=H", self.close_code) + payload
        payload = (
            int.from_bytes(payload, _BYTE_ORDER) ^
            (int.from_bytes(mask * (length >> 2) + mask[:length & 3], "big"))
        ).to_bytes(length, "big")

        return header + mask + payload
