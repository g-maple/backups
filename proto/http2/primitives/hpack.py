import struct
import typing
from .huffman import encode_huffman, decode_huffman

__all__ = [
    "HeaderBlockFragment",
    "HeaderIndexTable",
    "encode_integer",
    "encode_string",
    "decode_integer",
    "decode_string"
]
_STATIC_TABLE_INDEXES = [
    (None,                              None),
    (b':authority',                     None),
    (b':method',                        b'GET'),
    (b':method',                        b'POST'),
    (b':path',                          b'/'),
    (b':path',                          b'/index.html'),
    (b':scheme',                        b'http'),
    (b':scheme',                        b'https'),
    (b':status',                        b'200'),
    (b':status',                        b'204'),
    (b':status',                        b'206'),
    (b':status',                        b'304'),
    (b':status',                        b'400'),
    (b':status',                        b'404'),
    (b':status',                        b'500'),
    (b'ACCEPT-CHARSET',                 None),
    (b'ACCEPT-ENCODING',                b'gzip, deflate'),
    (b'ACCEPT-LANGUAGE',                None),
    (b'ACCEPT-RANGES',                  None),
    (b'ACCEPT',                         None),
    (b'ACCESS-CONTROL-ALLOW-ORIGIN',    None),
    (b'AGE',                            None),
    (b'ALLOW',                          None),
    (b'AUTHORIZATION',                  None),
    (b'CACHE-CONTROL',                  None),
    (b'CONTENT-DISPOSITION',            None),
    (b'CONTENT-ENCODING',               None),
    (b'CONTENT-LANGUAGE',               None),
    (b'CONTENT-LENGTH',                 None),
    (b'CONTENT-LOCATION',               None),
    (b'CONTENT-RANGE',                  None),
    (b'CONTENT-TYPE',                   None),
    (b'COOKIE',                         None),
    (b'DATE',                           None),
    (b'ETAG',                           None),
    (b'EXPECT',                         None),
    (b'EXPIRES',                        None),
    (b'FROM',                           None),
    (b'HOST',                           None),
    (b'IF-MATCH',                       None),
    (b'IF-MODIFIED-SINCE',              None),
    (b'IF-NONE-MATCH',                  None),
    (b'IF-RANGE',                       None),
    (b'IF-UNMODIFIED-SINCE',            None),
    (b'LAST-MODIFIED',                  None),
    (b'LINK',                           None),
    (b'LOCATION',                       None),
    (b'MAX-FORWARDS',                   None),
    (b'PROXY-AUTHENTICATE',             None),
    (b'PROXY-AUTHORIZATION',            None),
    (b'RANGE',                          None),
    (b'REFERER',                        None),
    (b'REFRESH',                        None),
    (b'RETRY-AFTER',                    None),
    (b'SERVER',                         None),
    (b'SET-COOKIE',                     None),
    (b'STRICT-TRANSPORT-SECURITY',      None),
    (b'TRANSFER-ENCODING',              None),
    (b'USER-AGENT',                     None),
    (b'VARY',                           None),
    (b'VIA',                            None),
    (b'WWW-AUTHENTICATE',               None)
]
_STATIC_TABLE_LENGTH = len(_STATIC_TABLE_INDEXES)


def encode_integer(integer: int, prefix: int, prefix_length: int) -> bytes:
    """
    Encodes a single integer primitives with
    proper padding and splitting across octets.
    :param integer: Integer to encode.
    :param prefix: Value to put before the integer.
    :param prefix_length: Number of bits available in the first octet.
    :return: Bytes in network-byte order.
    """
    prefix_value = (2 ** prefix_length) - 1
    if integer < prefix_value:
        return struct.pack(">B", (prefix << prefix_length) | integer)
    else:
        data = [struct.pack(">B", (prefix << prefix_length) | prefix_value)]
        integer -= prefix_value
        while integer >= 128:
            data.append(struct.pack(">B", 0x80 | (integer % 128)))
            integer //= 128
        data.append(struct.pack(">B", integer))
        return b''.join(data)


def decode_integer(data: bytes, prefix_length: int) -> typing.Tuple[int, int, int]:
    """
    Decodes an integer literal into it's parts.
    :param data: Bytes to decode.
    :param prefix_length: Number of bits available in the first octet.
    :return: The integer, the value before the integer, and the number of bytes consumed.
    """
    first_data = data[0] & (0xFF >> (8 - prefix_length))
    if len(data) == 1 or first_data < (2 ** prefix_length) - 1:
        return first_data, (data[0] & (0xFF << prefix_length)) >> prefix_length, 1
    else:
        prefix = (data[0] & (0xFF << prefix_length)) >> prefix_length
        integer = first_data
        exponent = 0
        octets = 1

        for byte in data[1:]:
            integer += (byte & 0x7F) * (2 ** exponent)
            exponent += 7
            octets += 1
            if not byte & 0x80:
                break

        return integer, prefix, octets


def encode_string(data: bytes, huffman: bool=False) -> bytes:
    """
    Encodes a string literal into bytes. Optional huffman encoding.
    :param data: Byte string to encode.
    :param huffman: If True, will encode the literal using the HPACK huffman encoding.
    :return: Bytes in network byte order.
    """
    if huffman:
        data = encode_huffman(data)
    return encode_integer(len(data), 1 if huffman else 0, 7) + data


def decode_string(data: bytes) -> typing.Tuple[bytes, int]:
    """
    Decodes a string literal encoded into bytes.
    :param data: Data to decode into a string literal.
    :return: String literal and number of bytes consumed.
    """
    length, huffman, octets = decode_integer(data, 7)
    string = data[octets:octets+length]  # type: bytes
    if huffman:
        return decode_huffman(string), octets + length
    return string, octets + length


class HeaderBlockFragment:
    pass


class HeaderIndexTable:
    def __init__(self):
        # Static table defined in RFC 7541 Appendix A
        # https://tools.ietf.org/html/rfc7541#appendix-A
        self._dynamic_encode = []  # type: typing.List[typing.Tuple[bytes, bytes]]
        self._dynamic_decode = []  # type: typing.List[typing.Tuple[bytes, bytes]]
        self._max_size_encode = 0
        self._max_size_decode = 0
        self._non_indexed_names = set()

    def get_decode_table(self):
        for i in _STATIC_TABLE_INDEXES:
            yield i
        for i in self._dynamic_decode:
            yield i

    def get_encode_table(self):
        for i in _STATIC_TABLE_INDEXES:
            yield i
        for i in self._dynamic_encode:
            yield i

    def get_size_decode_entries(self) -> int:
        length = 0
        for name, value in self._dynamic_decode:
            length += len(name) + len(value)
        return length + (len(self._dynamic_decode) << 5)

    def get_size_encode_entries(self) -> int:
        length = 0
        for name, value in self._dynamic_encode:
            length += len(name) + len(value)
        return length + (len(self._dynamic_encode) << 5)

    def add_decode_entry(self, name: bytes, value: bytes):
        self._dynamic_decode.insert(0, (name, value))
        self.evict_decode_entries()

    def add_encode_entry(self, name: bytes, value: bytes):
        self._dynamic_encode.insert(0, (name, value))
        self.evict_encode_entries()

    def evict_decode_entries(self):
        length = self.get_size_decode_entries()
        while length > self._max_size_decode:
            name, value = self._dynamic_decode.pop(-1)
            length -= len(name) + len(value) + 32

    def evict_encode_entries(self):
        length = self.get_size_encode_entries()
        while length > self._max_size_encode:
            name, value = self._dynamic_encode.pop(-1)
            length -= len(name) + len(value) + 32

    def get_decode_index(self, index: int) -> typing.Tuple[bytes, bytes]:
        if index < _STATIC_TABLE_LENGTH:
            return _STATIC_TABLE_INDEXES[index]
        else:
            return self._dynamic_decode[index - _STATIC_TABLE_LENGTH]

    def get_encode_index(self, index: int) -> typing.Tuple[bytes, bytes]:
        if index < _STATIC_TABLE_LENGTH:
            return _STATIC_TABLE_INDEXES[index]
        else:
            return self._dynamic_encode[index - _STATIC_TABLE_LENGTH]

    def decode_table_length(self) -> int:
        return len(self._dynamic_decode) + _STATIC_TABLE_LENGTH

    def encode_table_length(self) -> int:
        return len(self._dynamic_encode) + _STATIC_TABLE_LENGTH

    def encode_header_block(self, headers: typing.List[typing.Tuple[bytes, bytes]], allow_huffman=True, allow_index=True, never_index=False) -> bytes:
        header_block = []
        for name, value in headers:
            best_index = -1
            both_index = False
            for index, ipair in enumerate(self.get_encode_table()):
                iname, ivalue = ipair
                if iname == name:
                    if best_index == -1:
                        best_index = index
                        if not allow_index:
                            break
                    elif ivalue == value:
                        best_index = index
                        both_index = True
                        break
            if both_index:
                header_block.append(encode_integer(best_index, 1, 7))
            else:
                if never_index:
                    if best_index == -1:
                        header_block.append(encode_integer(0, 1, 4))
                        header_block.append(encode_string(name, allow_huffman))
                    else:
                        header_block.append(encode_integer(best_index, 1, 4))
                    header_block.append(encode_string(value, allow_huffman))

                elif allow_index:
                    if best_index == -1:
                        header_block.append(encode_integer(0, 1, 6))
                        header_block.append(encode_string(name, allow_huffman))
                        header_block.append(encode_string(value, allow_huffman))
                    else:
                        header_block.append(encode_integer(best_index, 1, 6))
                        header_block.append(encode_string(value, allow_huffman))
                    self.add_encode_entry(name, value)

                else:
                    if best_index == -1:
                        header_block.append(encode_integer(0, 0, 4))
                        header_block.append(encode_string(name, allow_huffman))
                    else:
                        header_block.append(encode_integer(best_index, 0, 4))
                    header_block.append(encode_string(value, allow_huffman))

        return b''.join(header_block)

    def encode_dynamic_table_size_update(self, size: int) -> bytes:
        self._max_size_encode = size
        self.evict_encode_entries()
        return encode_integer(size, 0b100, 5)

    def decode_header_block(self, data: bytes) -> typing.Tuple[typing.List[typing.Tuple[bytes, bytes]], int]:
        data_length = len(data)
        offset = 0
        headers = []
        while offset < data_length:
            name = None
            value = None

            # 6.1 Indexed Header Field
            if data[offset] & 0x80:
                index, _, consumed = decode_integer(data[offset:], 7)
                offset += consumed
                name, value = self.get_decode_index(index)

            # 6.2.1 Literal Header Value with Incremental Indexing
            elif data[offset] & 0xC0 == 0x40:
                index, _, consumed = decode_integer(data[offset:], 6)
                offset += consumed
                if index > 0:
                    name, _ = self.get_decode_index(index)
                    value, consumed = decode_string(data[offset:])
                    offset += consumed
                else:
                    name, consumed = decode_string(data[offset:])
                    offset += consumed
                    value, consumed = decode_string(data[offset:])
                    offset += consumed

                # Add the entry to the dynamic table and evict entries.
                self.add_decode_entry(name, value)

            # 6.2.2 Literal Header Field Without Indexing
            elif data[offset] & 0xF0 == 0x00:
                index, _, consumed = decode_integer(data[offset:], 4)
                offset += consumed
                if index > 0:
                    name, _ = self.get_decode_index(index)
                    value, consumed = decode_string(data[offset:])
                    offset += consumed
                else:
                    name, consumed = decode_string(data[offset:])
                    offset += consumed
                    value, consumed = decode_string(data[offset:])
                    offset += consumed

            # 6.2.3 Literal Header Field Never Indexed
            elif data[offset] & 0xF0 == 0x10:
                index, _, consumed = decode_integer(data[offset:], 4)
                offset += consumed
                if index > 0:
                    name, _ = self.get_decode_index(index)
                    value, consumed = decode_string(data[offset:])
                    offset += consumed
                else:
                    name, consumed = decode_string(data[offset:])
                    offset += consumed
                    value, consumed = decode_string(data[offset:])
                    offset += consumed

            # 6.3 Dynamic Table Size Update
            elif data[offset] & 0xE0 == 0x20:
                max_size, _, consumed = decode_integer(data[offset:], 5)
                self._max_size_decode = max_size
                self.evict_encode_entries()

            # Invalid Prefix.
            else:
                break

            if name is not None:
                headers.append((name, value))

        return headers, offset
