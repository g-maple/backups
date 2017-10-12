import typing

__all__ = [
    "Http2Stream",

    "STREAM_STATE_IDLE",
    "STREAM_STATE_RESERVED_LOCAL",
    "STREAM_STATE_RESERVED_REMOTE",
    "STREAM_STATE_OPEN",
    "STREAM_STATE_HALF_CLOSED_LOCAL",
    "STREAM_STATE_HALF_CLOSED_REMOTE",
    "STREAM_STATE_CLOSED"
]

STREAM_STATE_IDLE = 0
STREAM_STATE_RESERVED_LOCAL = 1
STREAM_STATE_RESERVED_REMOTE = 2
STREAM_STATE_OPEN = 3
STREAM_STATE_HALF_CLOSED_LOCAL = 4
STREAM_STATE_HALF_CLOSED_REMOTE = 5
STREAM_STATE_CLOSED = 6


class Http2Stream:
    def __init__(self, stream_id: int, context):
        self.stream_id = stream_id
        self.state = STREAM_STATE_IDLE
        self.priority = 0
        self.weight = 16
        self.parent = None  # type: Http2Stream
        self.children = []  # type: typing.List[Http2Stream]
        self.context = context

    def __eq__(self, other):
        return isinstance(other, Http2Stream) and self.stream_id == other.stream_id

    def __repr__(self):
        return "<Http2Stream id={} children={}>".format(self.stream_id, self.children)

    def find_child(self, stream):
        if self == stream:
            return self
        for child in self.children:
            result = child.find_child(stream)
            if result is not None:
                return result
        return None

    def add_child(self, stream, exclusive: bool):
        # If the dependency is our parent, then we replace ourselves with their position.
        if self.has_parent(stream):
            if stream.parent is not None:
                stream.parent.children.remove(stream)
                stream.parent.children.append(self)
                self.parent = stream.parent
            else:
                self.parent = None
            stream.parent = self

            # Depending on exclusive flag, keep our children or give to our new child.
            if exclusive:
                for child in self.children:
                    child.parent = stream
                stream.children.extend(self.children)
                self.children = [stream]
            else:
                self.children.append(stream)

        # Otherwise we add to our children.
        else:
            if exclusive:
                stream.parent = self
                stream.children = self.children
                for child in self.children:
                    child.parent = stream
                self.children = [stream]
            else:
                stream.parent = self
                self.children.append(stream)

    def remove_child(self, stream):
        child = self.find_child(stream)
        if child is not None:
            if child.parent is not None:
                for cchild in child.children:
                    cchild.parent = child.parent
                child.parent.children.remove(child)
                child.parent.children.extend(child.children)

    def has_child(self, stream):
        for child in self.children:
            if child == stream:
                return True
            if child.has_child(stream):
                return True
        return False

    def has_parent(self, stream):
        return self.parent is not None and (self.parent == stream or self.parent.has_parent(stream))

    def close(self):
        if self.parent:
            for child in self.children:
                child.parent = self.parent
                self.parent.children.append(child)
        self.state = STREAM_STATE_CLOSED
