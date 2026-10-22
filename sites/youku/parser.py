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

        if data == [] or ("error" in data and data.get("error").get("code") in (1012, 120020001)):
            status = 'NULL'
            info = data.get("error").get("description") if "error" in data else None
            '''
            save_raw = False
            if save_raw:
                RAW_DIR = Path("./raw")
                RAW_DIR.mkdir(exist_ok=True)
                raw_file = RAW_DIR / f"{vid}.json"
                raw_file.write_text(text, encoding="utf-8")
            '''
            return status, info, row, None
        elif "title" in data:
            status = 'OK'
            row["title"] = data.get("title")
            row["duration"] = data.get("duration")
            row["state"] = data.get("duration")
            row["created"] = data.get("duration")
            row["published"] = data.get("published")
            row["description"] = data.get("description")
            row["public_type"] = data.get("description")
            row["user_id"] = data.get("user", {}).get("id")
            row["tags"] = data.get("tags")
            return status, row["title"], row, None
        elif "error" in data and data.get("error").get("code") == 1015:
            raise YoukuAPIError(data.get("error").get("code"), data.get("error").get("type"), data.get("error").get("description"))

        return "ERROR", data.get("error", {}).get("description"), row, None


    async def _handle_exception(self, item, row, exception):
        if exception.code == 120020001:
            return "NULL", exception.description, row, None
        else:
            return "ERROR", exception.description, row, None

class YoukuAPIError(ParserError):

    def __init__(self, code, type, description):
        self.code = code
        self.type = type
        self.description = description
