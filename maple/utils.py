import typing


class MapleError(Exception):
    """
    maple 基础错误类。

    所有错误类均基于此类。
    """
    pass


def ensure_bytes(value: typing.Any) -> bytes:
    """
    确保传入变量是字节对象
    :param value: 任意类型
    :return: bytes
    """
    if isinstance(value, bytes):
        return value

    if isinstance(value, bytearray):
        return bytes(value)

    if value is None:
        return b""

    if not isinstance(value, str):
        str_value = str(value)
    else:
        str_value = value

    return str_value.encode('utf-8')


def ensure_str(value: typing.Any) -> str:
    """
    确保传入变量是字符串对象
    :param value: 任何类型
    :return: str
    """
    if isinstance(value, str):
        return value

    if value is None:
        return ''

    if isinstance(value, (bytes, bytearray)):
        str_value = value.decode('utf-8')
    else:
        str_value = value

    return str(str_value)
