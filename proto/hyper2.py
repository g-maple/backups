import typing

from h2.connection import H2Connection
from h2.events import DataReceived, RequestReceived, StreamEnded, StreamReset, WindowUpdated, ConnectionTerminated
from h2.errors import *

from .abc import AbstractWebProtocol
from .http import HttpRequest, HttpResponse


class Hyper2WebProtocol(AbstractWebProtocol):
    def __init__(self, base):
        self.server = base.server
        self._conn = H2Connection(client_side=False, header_encoding=False)
        self._requests = {}  # type: typing.Dict[int, HttpRequest]
        self._window = {}  # type: typing.Dict[int, int]
        self._responses = []  # type: typing.List[HttpResponse]
        AbstractWebProtocol.__init__(self, base)

    def open(self, transport):
        self._transport = transport
        self._conn.initiate_connection()
        self._transport.write(self._conn.data_to_send())

    def receive_data(self, data: bytes):
        events = self._conn.receive_data(data)

        for event in events:
            if isinstance(event, RequestReceived):
                request = HttpRequest()
                request._extra["stream_id"] = event.stream_id
                request.version = b'2'
                for key, value in event.headers:
                    if key[0] == 58:  # ord(":") == 58
                        if key == b':method':
                            request.method = value
                        elif key == b':authority':
                            request.headers[b'Server'] = value
                        elif key == b':path' and value != b'*':
                            request.on_url(value)
                    else:
                        request.headers[key] = request.headers.get(key, []) + [value]
                self._requests[event.stream_id] = request
                self._window[event.stream_id] = self._conn.remote_flow_control_window(event.stream_id)

            elif isinstance(event, DataReceived):
                try:
                    request = self._requests[event.stream_id]
                except KeyError:
                    self._conn.reset_stream(event.stream_id, PROTOCOL_ERROR)
                    return
                request.body += event.data
                self._conn.increment_flow_control_window(event.flow_controlled_length, 0)
                self._conn.increment_flow_control_window(event.flow_controlled_length, event.stream_id)

            elif isinstance(event, WindowUpdated):
                if event.stream_id == 0:
                    for stream_id in self._window:
                        self._window[stream_id] += event.delta
                else:
                    self._window[event.stream_id] += event.delta
                self._update_window_size()

            elif isinstance(event, StreamEnded):
                self.receive_message(self._requests[event.stream_id])

            elif isinstance(event, StreamReset):
                if event.stream_id in self._requests:
                    del self._requests[event.stream_id]
                    del self._window[event.stream_id]

            elif isinstance(event, ConnectionTerminated):
                self.close()

        self._transport.write(self._conn.data_to_send())

    def receive_message(self, message: HttpRequest):
        self.loop.create_task(self.server.http_handler(self, message))

    def _update_window_size(self):
        for response in self._responses[:]:
            stream_id = response._extra["request"]._extra["stream_id"]
            if self._window[stream_id] < len(response):
                continue
            headers = [(b":status", b'%d' % response.status_code)]
            for key, value in response.headers.items():
                headers.append((key.lower(), b', '.join(value)))
            self._conn.send_headers(stream_id, headers)
            self._conn.send_data(stream_id, response.body, end_stream=True)
            del self._window[stream_id]
            del self._requests[stream_id]
            self._responses.remove(response)
        self._transport.write(self._conn.data_to_send())

    def send_message(self, message: HttpResponse):
        self._responses.append(message)
        self._update_window_size()
