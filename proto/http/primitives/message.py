import datetime
import gzip
import json
import io
import re
import sys
import typing
import zlib
import brotli
import cchardet
from .headers import HttpHeaders
from ...abc import AbstractMessage
from ...common.cookies import Cookies, Cookie, _COOKIE_EXPIRE_FORMAT

__all__ = [
    "HttpMessage"
]
_COOKIE_REGEX = re.compile(b'([^\\s=;]+)(?:=([^;]+))?(?:;|$)')
_CHARSET_REGEX = re.compile(b'[^/]+/[^/]+;\s*charset=([^=;]+)')
_COOKIE_META = {b'domain', b'path', b'expires', b'maxage', b'httponly', b'secure'}
_SUPPORTED_ENCODINGS = {b'gzip', b'deflate', b'br', b'identity'}


class HttpMessage(AbstractMessage):
    def __init__(self):
        self.headers = HttpHeaders()
        self.cookies = Cookies()
        self.version = b''
        self._extra = {}

        self._body = b''
        self._body_len = 0
        self._body_buffer = []
        self._header_buffer = []
        self._is_header_complete = False
        self._is_complete = False
        AbstractMessage.__init__(self)

    def __len__(self) -> int:
        return self._body_len

    def is_complete(self) -> bool:
        return self._is_complete

    def is_header_complete(self) -> bool:
        return self._is_header_complete

    def to_bytes(self) -> bytes:
        raise NotImplementedError("HttpMessage.to_bytes() is not implemented.")

    def set_encoding(self, encoding: bytes, set_headers: bool=True) -> None:
        """
        Sets the encoding of the body to be a certain Content-Encoding.
        Currently the only supported encodings are identity, gzip, delfate, and brotli.
        :param encoding: Encoding to set the body to be.
        :param set_headers: If True, modifies the headers to reflect the change.
        :return: None
        """
        assert encoding in _SUPPORTED_ENCODINGS
        current_encoding = self.headers.get(b'Content-Encoding', [b'identity'])[0]
        if current_encoding == encoding or not self._body_len:
            return  # No-op if the encoding is already correct.

        # Decoding the current encoding.
        if current_encoding != b'identity':
            if current_encoding == b'br':
                self.body = brotli.decompress(self.body)
            elif current_encoding == b'gzip':
                self.body = gzip.GzipFile(fileobj=io.BytesIO(self.body), mode="rb").read()
            elif current_encoding == b'deflate':
                self.body = zlib.decompress(self.body, -zlib.MAX_WBITS)

        # Re-encoding with the desired encoding.
        if encoding != b'identity':
            if encoding == b'br':
                self.body = brotli.compress(self.body)
            elif encoding == b'gzip':
                out = io.BytesIO()
                gzip.GzipFile(fileobj=out, mode="wb").write(self.body)
                self.body = out.getvalue()
            elif encoding == b'deflate':
                deflate = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
                self.body = deflate.compress(self.body) + deflate.flush()

        # Optionally set the headers.
        if set_headers:
            self.headers[b'Content-Length'] = b'%d' % self._body_len
            self.headers[b'Content-Encoding'] = encoding

    def body_string(self) -> str:
        """
        Decodes the body of the HTTP message as a string
        while attempting to decode the body. If the body is
        not in an 'identity' character encoding, does the decoding
        and puts the body back into the encoding.
        :return: Body decoded as a string.
        """
        # If the body is encoded or compressed, need to decompress it before getting the string.
        encoding = self.headers.get(b'Content-Encoding', [b'identity'])[0]
        if encoding != b'identity':
            self.set_encoding(b'identity', set_headers=False)
        body = None

        # If the headers are giving us a hint, then try them first.
        charset = _CHARSET_REGEX.match(self.headers.get(b'Content-Type', [b''])[0])
        if charset is not None:
            charset = charset.group(1).decode("utf-8")
            try:
                body = self.body.decode(charset)
            except UnicodeDecodeError:
                pass

        # Otherwise try the system default encoding followed by cchardet attempting to detect encoding.
        if body is None:
            try:
                body = self.body.decode(sys.getdefaultencoding())
            except UnicodeDecodeError:
                body = self.body.decode(cchardet.detect(self.body)["encoding"])

        # Revert back to the old encoding.
        if encoding != b'identity':
            self.set_encoding(encoding, set_headers=False)

        return body

    def body_json(self, loads=json.loads, *args, **kwargs) -> typing.Union[dict, list]:
        """
        Loads the body as a JSON object if it is valid JSON.
        :param loads: Function to load the body as JSON with. Default: json.loads
        :return: The body as JSON.
        """
        return loads(self.body_string(), *args, **kwargs)

    @property
    def body(self) -> bytes:
        return self._body

    @body.setter
    def body(self, body: bytes):
        self._body = body
        self._body_len = len(body)

    # httptools parser interface

    def on_header(self, key: typing.Optional[bytes], val: typing.Optional[bytes]):
        self._header_buffer.append((key, val))
        print(key, val)

    def on_headers_complete(self) -> None:
        _headers = {}
        _key_buffer = []
        _val_buffer = []
        _key = None
        for key, val in self._header_buffer:
            if key is not None:
                if _key_buffer is None:
                    _key_buffer = [key]
                    if _key is not None:
                        if _key in _headers:
                            _headers[_key].append(b''.join(_val_buffer))
                        else:
                            _headers[_key] = [b''.join(_val_buffer)]
                    _key = None
                else:
                    _key_buffer.append(key)
            if val is not None:
                if _key is None:
                    _key = b''.join(_key_buffer)
                    _key_buffer = None
                    _val_buffer = []
                _val_buffer.append(val)
        if _key is not None:
            if _key in _headers:
                _headers[_key].append(b''.join(_val_buffer))
            else:
                _headers[_key] = [b''.join(_val_buffer)]

        self.headers.update(_headers)
        if b'Cookie' in self.headers:

            # Add a single cookie for a b'Cookie' header.
            cookie = Cookie(domain=_headers.get(b'Host', [None])[0])

            for cookie_header in self.headers[b'Cookie']:
                for key, value in _COOKIE_REGEX.findall(cookie_header):
                    cookie.values[key] = value

            self.cookies.add(cookie)
            del self.headers[b'Cookie']

        elif b'Set-Cookie' in self.headers:
            for cookie_header in self.headers[b'Set-Cookie']:
                cookie = Cookie()
                for key, value in _COOKIE_REGEX.findall(cookie_header):
                    key_lower = key.lower()
                    if key_lower in _COOKIE_META:
                        if key_lower == b'secure':
                            cookie.secure = True
                        elif key_lower == b'httponly':
                            cookie.http_only = True
                        elif key_lower == b'domain':
                            cookie.domain = value
                        elif key_lower == b'path':
                            cookie.path = value
                        elif key_lower == b'expires':
                            try:
                                cookie.expires = datetime.datetime.strptime(value.decode("utf-8"), _COOKIE_EXPIRE_FORMAT)
                            except ValueError:
                                pass
                            except UnicodeDecodeError:
                                pass
                        else:
                            try:
                                cookie.max_age = int(value)
                            except ValueError:
                                pass
                            except UnicodeDecodeError:
                                pass
                    else:
                        cookie.values[key] = value
                self.cookies.add(cookie)
            del self.headers[b'Set-Cookie']

        self._is_header_complete = True

    def on_body(self, body: bytes) -> None:
        self._body_buffer.append(body)

    def on_message_complete(self) -> None:
        self._body = b''.join(self._body_buffer)
        self._body_len = len(self._body)
        self._is_complete = True
