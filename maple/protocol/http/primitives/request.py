from .message import HttpMessage

class HttpRequest(HttpMessage):
    def is_complete(self):
        pass

    def to_bytes(self):
        pass