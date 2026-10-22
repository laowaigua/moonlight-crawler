# base.py

import aiohttp
import socket
import asyncio
from fake_useragent import UserAgent

class ParserError(Exception):
    pass


_USER_AGENT = None
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _get_user_agent():
    """Reuse fake_useragent's local data instead of reloading it per item."""
    global _USER_AGENT
    if _USER_AGENT is None:
        try:
            _USER_AGENT = UserAgent()
        except Exception:
            return _DEFAULT_USER_AGENT
    try:
        return _USER_AGENT.random
    except Exception:
        return _DEFAULT_USER_AGENT

def retry(times=5, delay=1):
    def deco(func):
        if times <= 0:
            return func
        async def wrapper(*args, **kwargs):
            last_exception = None
            for i in range(times):
                try:
                    return await func(*args, **kwargs)
                except asyncio.CancelledError:
                    raise
                except (aiohttp.ClientError, socket.error, ParserError) as e:
                    if isinstance(e, aiohttp.ClientConnectionError) and "Connector is closed" in str(e):
                        raise
                    last_exception = e
                    if i < times - 1:
                        await asyncio.sleep(delay * (i + 1))
            if last_exception:
                raise last_exception
            return None
        return wrapper
    return deco

'''
def retry(times=5, delay=1):
    def deco(func):
        async def wrapper(*args, **kwargs):
            for i in range(times):
                try:
                    return await func(*args, **kwargs)
                except (aiohttp.ClientError, socket.error, ParserError) as e:
                    last_exception = e
                    await asyncio.sleep(delay * (i + 1))
            if last_exception:
                raise last_exception
            else:
                return None
        return wrapper
    return deco
'''

class BaseParser:

    name: str
    schema: dict

    async def fetch(self, item, session):
        """
        公共 fetch 框架，异常 row 由子类处理
        """
        row = {key: None for key in self.schema}

        headers = {
            "User-Agent": _get_user_agent(),
            "Accept": "application/json,text/html,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }

        """
        blob = [
            ("vid_0.jpg", bytes_0),
            ("vid_1.jpg", bytes_1),
            ...   
        ]
        """

        try:
            status, info, row, blob = await self._fetch_data(item, session, headers, row)
        except (aiohttp.ClientError,socket.error) as e:
            status, info, row, blob = "ERROR", str(e), row, None
        except ParserError as e:
            status, info, row, blob = await self._handle_exception(item, row, e)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # ← 新增
            status, info, row, blob = "ERROR", f"{type(e).__name__}: {e}", row, None

        return status, info, row, blob

    async def _fetch_data(self, item, session, headers, row):
        """
        子类必须实现，返回 status, info, row, blob
        """
        raise NotImplementedError

    async def _handle_exception(self, item, row, exception):
        """
        默认异常处理，子类可以覆盖
        """
        return "ERROR", str(exception), row, None
