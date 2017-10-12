import asyncio
import typing
from .cookie_jar import AbstractCookieJar, CookieJar
from .session import ClientSession
from ..proto.http import HttpResponse

__all__ = [
    "ClientSessionPool"
]


class ClientSessionPool:
    def __init__(self, pool_size: int, loop: asyncio.AbstractEventLoop=None, version: bytes=b'1.1',
                 cookie_jar: AbstractCookieJar=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._semaphore = asyncio.Semaphore(value=pool_size, loop=self._loop)
        self.cookie_jar = cookie_jar if cookie_jar is not None else CookieJar()
        self._connections = [ClientSession(
            loop=loop, version=version, cookie_jar=self.cookie_jar
        ) for _ in range(pool_size)]
        self._reserved = 0

    async def acquire_session(self) -> ClientSession:
        await self._semaphore.acquire()
        for i, connection in enumerate(self._connections):
            mask = (1 << i)
            if self._reserved & mask == 0:
                self._reserved |= mask
                return connection
        return None

    async def release_session(self, session: ClientSession) -> None:
        for i, connection in enumerate(self._connections):
            if connection == session:
                self._reserved &= ~(1 << i)
                break
        self._semaphore.release()

    async def request(self, url: bytes, method: bytes,
                        headers: typing.Dict[bytes, typing.Union[bytes, typing.Iterable[bytes]]]=None,
                        body: bytes=b'') -> HttpResponse:
        session = await self.acquire_session()
        response = await session.request(url, method, headers, body)
        await self.release_session(session)
        return response
