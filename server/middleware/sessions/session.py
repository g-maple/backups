__all__ = [
    "Session"
]


class Session(dict):
    def __init__(self, identity, data):
        self.identity = identity
        dict.update(self, data)
