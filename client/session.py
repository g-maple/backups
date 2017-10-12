import asyncio
import sys
import socket
import ssl as _ssl
import typing
import httptools
from .cookie_jar import CookieJar, AbstractCookieJar
from ..proto.http import HttpRequest, HttpResponse, HttpParser, HttpHeaders
from ..errors import SslCertificateVerificationError, SslError
from ..utils import safe_decode

__all__ = [
    "ClientSession"
]
_HTTP_REDIRECTS = {301, 302, 307, 308}
_PY36 = sys.version_info > (3, 6)  # TCP_NODELAY is set by default on asyncio sockets Python 3.6+
_SET_TCP_NODELAY = hasattr(socket, "TCP_NODELAY") and not _PY36


class ClientSession:
    def __init__(self, loop: asyncio.AbstractEventLoop=None,
                 headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None,
                 version: bytes=b'1.1', cookie_jar: AbstractCookieJar=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._lock = asyncio.Lock(loop=self._loop)
        self._reader = None  # type: asyncio.StreamReader
        self._writer = None  # type: asyncio.StreamWriter
        self._version = version
        self._host = None
        self._port = None
        self._parser = HttpParser()
        self.cookie_jar = cookie_jar if cookie_jar is not None else CookieJar()
        self.headers = HttpHeaders()
        if headers is not None:
            self.headers.update(self.headers)

    def __del__(self):
        if self._writer is not None:
            self._writer.close()
        self._writer = None
        self._reader = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open(self, address: typing.Tuple[bytes, int], ssl: typing.Optional[_ssl.SSLContext]=None) -> None:
        """
        Opens a connection to the address and verifies the SSL/TLS certificate if specified.

        :param address: Tuple of host and port to connect to.
        :param ssl: Optional SSLContext, if not given and using HTTPS will use the system default SSLContext.
        :return: None
        """
        host, port = address
        if self._reader is None or self._host != host or self._port != port:
            async with self._lock:
                if self._reader is not None:
                    self._writer.close()
                try:
                    self._reader, self._writer = await asyncio.open_connection(
                        host=safe_decode(host), port=port,
                        loop=self._loop, ssl=ssl
                    )

                    # Set TCP_NODELAY to allow writes to be minimally buffered.
                    if _SET_TCP_NODELAY:
                        sock = self._writer.transport.get_extra_info("socket")
                        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, True)

                except _ssl.SSLError as error:
                    if "CERTIFICATE_VERIFY_FAILED" in str(error):
                        raise SslCertificateVerificationError("Error occurred while verifying the certificate.")
                    else:
                        raise SslError(str(error))
                except _ssl.CertificateError:
                    raise SslCertificateVerificationError("Certificate is invalid or expired.")
                self._host = host
                self._port = port

    async def close(self) -> None:
        """
        Closes a connection if one is open.
        :return: None
        """
        async with self._lock:
            if self._reader is not None:
                self._writer.close()
            self._reader = None
            self._writer = None

    def is_closed(self) -> bool:
        return self._writer is None

    async def request(self, url: bytes, method: bytes, headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None,
                        body: bytes=b'', allow_redirects: bool=True, max_redirects: int=10,
                        buffer_length: int=65536, ssl: _ssl.SSLContext=None, timeout=10) -> HttpResponse:
        """
        Submits a request to the URL given in the function. The request inherits all
        values that are given to it by the ClientSession including HTTP version, headers,
        cookies (if applicable for that domain) as well as all values passed in to the
        function. Uses the system default for SSL/TLS on HTTPS unless given a different
        SSLContext. Follow redirects by default but the behaviour can be overridden.

        :param url: URL to send the request to.
        :param method: HTTP method to use.
        :param headers: Headers to apply to the request.
        :param body: Body of the request.
        :param allow_redirects: If True, allow the request to automatically respond to redirects.
        :param max_redirects: Maximum number of redirects allowed before canceling request.
        :param buffer_length: Maximum nuber of bytes to read per cycle of reading and parsing.
        :param ssl: SSLContext object if the system default SSL/TLS context is not acceptable.
        :param timeout: Number of seconds to wait before timing out.
        :return: HttpResponse object.
        """
        parsed_url = httptools.parse_url(url)
        host = parsed_url.host

        # If the connection is HTTPS default port is 443, otherwise 80.
        if parsed_url.schema.lower() == b'https':
            port = parsed_url.port if parsed_url.port else 443
            if ssl is None:
                ssl = _ssl.create_default_context()
        else:
            port = parsed_url.port if parsed_url.port else 80

        # Create the request.
        request = HttpRequest()
        request.method = method
        request.version = self._version
        request.body = body
        request.headers[b'Host'] = host
        request.on_url(url)

        # Apply headers.
        for key, val in self.headers.items():
            request.headers[key] = val
        if headers is not None:
            for key, val in headers.items():
                request.headers[key] = val

        # Create an HttpCookies object from the CookieJar.
        request.cookies = self.cookie_jar.get_cookies_for_url(request.url)

        response = HttpResponse()
        response_error = False
        self._parser.set_target(response)

        await self.open((host, port), ssl=ssl)
        async with self._lock:
            self._writer.write(request.to_bytes())
            while True:
                data = await asyncio.wait_for(self._reader.read(buffer_length), timeout=timeout, loop=self._loop)
                if data:
                    self._parser.feed_data(data)
                    if response.is_complete():
                        break

        # Socket is unlocked at this point.
        if response.headers.get(b'Connection', [b''])[0] == b'close':
            await self.close()

        # If there's cookies to be added to the CookieJar, do so here.
        if response.cookies:
            self.cookie_jar.update_cookies(request.url, response.cookies.values())

        # If there are redirects and we're allowed to follow, then follow them.
        if allow_redirects and response.status_code in _HTTP_REDIRECTS:
            if max_redirects <= 0 or b'Location' not in response.headers:
                response_error = True
            else:
                response = await self.request(
                    (response.headers.get(b'Location') or response.headers.get(b'URI'))[0],
                    method, headers=headers, body=body, allow_redirects=True, max_redirects=max_redirects-1
                )

        # If we're erroring or the response isn't complete, return a 500.
        if response_error or not response.is_complete():
            response.version = self._version
            response.body = b''
            response.status_code = 500
            response.status = b'Internal Server Error'
            return response
        else:
            return response

    async def get(self, url: bytes,
                  headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None,
                  body: bytes=b'', allow_redirects: bool=True, max_redirects: int=10,
                  buffer_length: int=65536, ssl: _ssl.SSLContext=None) -> HttpResponse:
        """
        See documentation of ClientSession.request(). Uses similar function signature without 'method'.
        """
        return await self.request(url, b'GET', headers, body, allow_redirects, max_redirects, buffer_length, ssl)

    async def post(self, url: bytes, headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None,
                   body: bytes=b'', allow_redirects: bool=True, max_redirects: int=10,
                   buffer_length: int=65536, ssl: _ssl.SSLContext=None) -> HttpResponse:
        """
        See documentation of ClientSession.request(). Uses similar function signature without 'method'.
        """
        return await self.request(url, b'POST', headers, body, allow_redirects, max_redirects, buffer_length, ssl)

    async def options(self, url: bytes, headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None,
                   body: bytes=b'', allow_redirects: bool=True, max_redirects: int=10,
                   buffer_length: int=65536, ssl: _ssl.SSLContext=None) -> HttpResponse:
        """
        See documentation of ClientSession.request(). Uses similar function signature without 'method'.
        """
        return await self.request(url, b'OPTIONS', headers, body, allow_redirects, max_redirects, buffer_length, ssl)

    async def head(self, url: bytes, headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None,
                      body: bytes=b'', allow_redirects: bool=True, max_redirects: int=10,
                      buffer_length: int=65536, ssl: _ssl.SSLContext = None) -> HttpResponse:
        """
        See documentation of ClientSession.request(). Uses similar function signature without 'method'.
        """
        return await self.request(url, b'HEAD', headers, body, allow_redirects, max_redirects, buffer_length, ssl)

    async def patch(self, url: bytes, headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None,
                   body: bytes=b'', allow_redirects: bool=True, max_redirects: int=10,
                   buffer_length: int=65536, ssl: _ssl.SSLContext=None) -> HttpResponse:
        """
        See documentation of ClientSession.request(). Uses similar function signature without 'method'.
        """
        return await self.request(url, b'PATCH', headers, body, allow_redirects, max_redirects, buffer_length, ssl)
