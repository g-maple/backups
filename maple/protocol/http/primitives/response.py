from .message import HttpMessage

class HttpResponse(HttpMessage):
    def is_complete(self):
        pass

    def to_bytes(self):
        pass