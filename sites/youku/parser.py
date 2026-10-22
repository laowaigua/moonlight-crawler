# base.py

from sites.base import BaseParser, ParserError, retry
from .schema import SCHEMA

class Parser(BaseParser):

    name = "youku"
    schema = SCHEMA

    @retry(times=5)
    async def _fetch_data(self, item, session, headers, row):

        row["video_id"] = item

        CLIENT_ID = '8ffbe901c4ea4b23'

        async with session.get(
            "https://openapi.youku.com/v2/videos/show.json",
            headers=headers,
            params={
                "video_id": item,
                "client_id": CLIENT_ID
            },
            timeout=60
        ) as r:
            r.raise_for_status()
            data = await r.json()
            #text = await r.text()

        if data == []:
            status = 'NULL'
            return status, None, row, None
        if not isinstance(data, dict):
            raise ParserError(f"Youku API returned an invalid response: {type(data).__name__}")

        error = data.get("error")
        error_code = error.get("code") if isinstance(error, dict) else None
        error_description = error.get("description") if isinstance(error, dict) else None

        if error_code in (1012, 120020001):
            return 'NULL', error_description, row, None
        elif "title" in data:
            status = 'OK'
            row["title"] = data.get("title")
            row["duration"] = data.get("duration")
            row["published"] = data.get("published")
            row["description"] = data.get("description")
            user = data.get("user")
            row["user_id"] = user.get("id") if isinstance(user, dict) else None
            row["tags"] = data.get("tags")
            return status, row["title"], row, None
        elif error_code == 1015:
            raise YoukuAPIError(error_code, error.get("type"), error_description)

        return "ERROR", error_description or f"Unexpected Youku API response: {data!r}", row, None


    async def _handle_exception(self, item, row, exception):
        if isinstance(exception, YoukuAPIError) and exception.code == 120020001:
            return "NULL", exception.description, row, None
        if isinstance(exception, YoukuAPIError):
            return "ERROR", exception.description, row, None
        return await super()._handle_exception(item, row, exception)

class YoukuAPIError(ParserError):

    def __init__(self, code, type, description):
        self.code = code
        self.type = type
        self.description = description
