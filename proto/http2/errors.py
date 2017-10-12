__all__ = [
    "Http2Error",
    "Http2ConnectionError",
    "Http2StreamError"
]


class Http2Error(Exception):
    pass


class Http2ConnectionError(Http2Error):
    def __init__(self, error_code: int):
        self.error_code = error_code


class Http2StreamError(Http2Error):
    def __init__(self, stream_id: int, error_code: int):
        self.stream_id = stream_id
        self.error_code = error_code
