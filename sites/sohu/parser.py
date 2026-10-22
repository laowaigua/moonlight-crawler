# base.py

from sites.base import BaseParser, ParserError, retry
from .schema import SCHEMA
import re
import html
from bs4 import BeautifulSoup

class Parser(BaseParser):

    name = "sohu"
    schema = SCHEMA

    @retry(times=5)
    async def _fetch_data(self, vid, session, headers, row):

        row["vid"] = vid

        url = f"http://my.tv.sohu.com/us/0/{vid}.shtml"

        async with session.get(
            url,
            headers=headers,
            timeout=60
        ) as r:
            r.raise_for_status()
            if str(r.url) == "https://tv.sohu.com/404/index.shtml":
                status = 'NULL'
                return status, None, row, None
            text = await r.text(encoding='utf-8', errors='ignore')
            soup = BeautifulSoup(text, "html.parser")

        def meta_content(attrs):
            meta = soup.find("meta", attrs)
            return meta.get("content") if meta else None

        def script_value(pattern, field):
            match = re.search(pattern, text)
            if not match:
                raise ParserError(f"Sohu page is missing {field}")
            return match.group(1)

        title = meta_content({"property": "og:title"})
        keywords = meta_content({"name": "keywords"})
        description = meta_content({"name": "description"})
        if title is None or keywords is None or description is None:
            missing = [name for name, value in (
                ("og:title", title), ("keywords", keywords), ("description", description)
            ) if value is None]
            raise ParserError(f"Sohu page is missing meta field(s): {', '.join(missing)}")

        row["title"] = html.unescape(title)
        try:
            row["videoLength"] = int(script_value(r"videoLength\s*:\s*['\"]([^'\"]+)['\"]", "videoLength"))
        except ValueError as exc:
            raise ParserError("Sohu page has an invalid videoLength") from exc
        row["uploadTime"] = script_value(r"uploadTime\s*:\s*['\"]([^'\"]+)['\"]", "uploadTime") + ":00"
        row["keywords"] = html.unescape(keywords.rsplit(',', 1)[0])
        row["description"] = html.unescape(description.split('：', 1)[-1])

        uid = re.search(r"uid\s*:\s*['\"]([^'\"]*)['\"]", text)
        if not uid:
            raise ParserError("Sohu page is missing uid")
        uid = uid.group(1)
        row["uid"] = uid if uid else None

        status = 'OK'
        return status, row["title"], row, None

        '''
        async with session.get(
            "https://my.tv.sohu.com/play/videonew.do",
            headers=headers,
            params={"vid": str(vid)},
            timeout=60
        ) as r:
            r.raise_for_status()
            data = await r.json()
        if data.get("status") == 5:
            status = 'NULL'
            return status, data.get("mytvmsg"), row, None
        elif data.get("status") == 1:
            row["tvName"] = html.unescape(data.get("data").get("tvName"))
            row["tag"] = html.unescape(data.get("data").get("tag"))
            row["myTvUid"] = data.get("data").get("myTvUid")
            row["totalDuration"] = data.get("data").get("totalDuration")

            status = 'OK'
            return status, row["tvName"], row, None
        elif data.get("status") == 11 or (data.get("status") == 5 and data.get("code") in (30, 104, 105, 1002)): # 视频设置了隐私 / 视频正在审核 / 该视频版权已到期 / 该账号已被冻结
            row = await self._fetch_data_from_html(session, headers, vid, row)
            status = 'OK'
            return status, row["tvName"], row, None
        '''
