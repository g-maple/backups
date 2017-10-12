import typing
from .frames import *
from .streams import *
from .hpack import HeaderIndexTable

__all__ = [
    "Http2Context",
    "Http2Settings"
]
_MAX_STREAM_ID = (2 ** 31) - 1


class Http2Settings:
    def __init__(self, context):
        self.context = context
        self.header_table_size = 4096
        self.enable_push = True
        self.max_concurrent_streams = -1
        self.initial_window_size = 65535
        self.max_frame_size = 16384
        self.max_header_list_size = -1


class Http2Context:
    def __init__(self):
        self.local_settings = Http2Settings(self)
        self.remote_settings = Http2Settings(self)
        self.header_index_table = HeaderIndexTable()
        self._closing = False
        self._last_stream_id = 0
        self.streams = {0: Http2Stream(0, self)}  # typing.Dict[int, Http2Stream]
        self.reserved_local = set()
        self.reserved_remote = set()
        self.frames = []  # typing.List[Http2Frame]

    def create_stream(self) -> typing.Optional[Http2Stream]:
        if self._closing:
            return None
        if self._last_stream_id == _MAX_STREAM_ID:
            self.close_connection(ERROR_CODE_REFUSED_STREAM)

        self._last_stream_id += 1
        for stream_id in range(self._last_stream_id):
            if stream_id in self.streams and self.streams[stream_id].state == STREAM_STATE_IDLE:
                self.close_stream(stream_id)

        stream = Http2Stream(self._last_stream_id, self)
        self.streams[stream.stream_id] = stream
        return stream

    def reserve_stream(self, stream_id: int) -> bool:
        if stream_id in self.reserved_remote:
            return False
        elif stream_id in self.reserved_local:
            return True
        else:
            if stream_id not in self.streams:
                return False
            stream = self.streams[stream_id]
            if stream.state != STREAM_STATE_IDLE:
                return False
            stream.state = STREAM_STATE_RESERVED_LOCAL
            self.reserved_local.add(stream_id)
            return True

    def close_stream(self, stream_id: int, error_code: int=None):
        if self._closing:
            return
        if stream_id in self.streams:
            stream = self.streams[stream_id]
            if stream.state == STREAM_STATE_HALF_CLOSED_LOCAL:
                return
            elif stream.state == STREAM_STATE_HALF_CLOSED_REMOTE:
                stream.state = STREAM_STATE_CLOSED
                del self.streams[stream_id]
            else:
                stream.state = STREAM_STATE_CLOSED

            if stream_id in self.reserved_local:
                self.reserved_local.remove(stream_id)
            if stream_id in self.reserved_remote:
                self.reserved_remote.remove(stream_id)

            frame = Http2RstStreamFrame()
            frame.error_code = error_code if error_code is not None else ERROR_CODE_PROTOCOL_ERROR
            self.frames.append(frame)

    def close_connection(self, error_code: int):
        if self._closing:
            return
        frame = Http2GoAwayFrame()
        frame.error_code = error_code
        self.frames.append(frame)
