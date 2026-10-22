# crawler.py
import asyncio
import aiohttp
import math


class Crawler:
    STATUS_PREFIX = {
        "OK": "",
        "NULL": "",
        "ERROR": ""
    }

    def __init__(self, parser, storager, chunk_size=100_000, concurrency=8, delay=0,
                 session_max_items=0):
        self.parser = parser
        self.storager = storager
        self.chunk_size = chunk_size
        self.sem = asyncio.Semaphore(concurrency)
        self.delay = delay
        self.session_max_items = max(0, session_max_items)

        self.print_settings = {
            "OK": True,
            "NULL": True,
            "ERROR": True
        }

        self.storage_settings = {
            "OK": True,
            "NULL": True,
            "ERROR": False
        }

    async def _fetch(self, item, session):
        async with self.sem:
            if self.delay > 0:
                await asyncio.sleep(self.delay / 1000)
            return await self.parser.fetch(item, session)

    async def _handle(self, item, session):
        status, info, row, blob = await self._fetch(item, session)
        if self.print_settings[status]:
            print(f"[Crawler][{self.parser.name}] {self.STATUS_PREFIX[status]}{item} {status:<6} {info}", flush=True)

        if self.storage_settings[status]:
            await self.storager.save_row(row, blob)

        if status == 'ERROR':
            await self.storager.record_error(item, info)

    async def run(self, items):
        await self.storager.start_writer()
        items = list(items)
        total = len(items)
        total_chunks = math.ceil(total / self.chunk_size) if total else 0
        print(f"[Crawler] Total items: {total}", flush=True)
        session = None
        session_items = 0
        session_number = 0

        try:
            for chunk_number, i in enumerate(range(0, total, self.chunk_size), start=1):
                chunk = items[i:i + self.chunk_size]
                print(
                    f"[Crawler] Processing Chunk {chunk_number}/{total_chunks} "
                    f"({i + 1} ~ {i + len(chunk)})",
                    flush=True,
                )

                # Keep the original chunk boundaries and progress reporting.
                # If the session limit falls inside a chunk, process subgroups
                # with separate sessions while retaining the same outer chunk.
                offset = 0
                while offset < len(chunk):
                    if session is None or (
                        self.session_max_items and session_items >= self.session_max_items
                    ):
                        if session is not None:
                            await session.close()
                        session = aiohttp.ClientSession()
                        session_number += 1
                        print(f"[Crawler] Created HTTP session #{session_number}", flush=True)
                        session_items = 0

                    remaining = len(chunk) - offset
                    if self.session_max_items:
                        remaining = min(
                            remaining,
                            self.session_max_items - session_items,
                        )
                    group = chunk[offset:offset + remaining]
                    tasks = [self._handle(item, session) for item in group]
                    await asyncio.gather(*tasks)
                    offset += len(group)
                    session_items += len(group)
        finally:
            if session is not None:
                await session.close()

        await self.storager.stop_writer()
        # self.storager.close()

    async def _record_error(self, item, error_info):
        await self.storager.record_error(item, error_info)
