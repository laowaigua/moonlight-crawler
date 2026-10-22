"""Parser for iQIYI Paopao feed records."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from sites.base import BaseParser, ParserError, retry
from .schema import SCHEMA


API_URL = "https://api-t.iqiyi.com/feed/get_feed"
SUCCESS_CODE = "A00000"
NOT_FOUND_CODE = "B00005"

FEED_FIELDS = (
    "feedId",
    "dataType",
    "status",
    "description",
    "releaseDate",
    "modifyDate",
    "userType",
    "sourceType",
    "extendType",
    "size",
    "wallId",
    "circleQipuId",
    "wallType",
    "wallName",
    "wallDesc",
    "master",
    "uid",
    "name",
    "tvIds",
    "albumId",
    "tvTitles",
    "thumbnails",
    "durations",
    "resolutions",
    "feedTitle",
    "pictures",
)

LIST_FIELDS = {
    "tvIds",
    "tvTitles",
    "thumbnails",
    "durations",
    "resolutions",
    "pictures",
}
BEIJING_TZ = ZoneInfo("Asia/Shanghai")


class Parser(BaseParser):
    name = "iqiyi_paopao"
    schema = SCHEMA

    # main_asyn.py performs one attempt per feed; avoid long retry stalls here too.
    @retry(times=1)
    async def _fetch_data(self, item, session, headers, row):
        try:
            base_id = int(item)
        except (TypeError, ValueError):
            raise ParserError(f"invalid iQIYI Paopao baseId: {item!r}")

        feed_id = base_id * 100 + 48
        row["baseId"] = base_id
        row["feedId"] = feed_id

        async with session.get(
            API_URL,
            params={"feedId": str(feed_id)},
            headers=headers,
            timeout=30,
        ) as response:
            response.raise_for_status()
            response_text = await response.text()

        try:
            # This endpoint can return JSON with a text/html content type.
            payload = json.loads(response_text)
        except json.JSONDecodeError:
            return (
                "ERROR",
                f"iQIYI Paopao API returned non-JSON content: {response_text[:200]!r}",
                row,
                None,
            )

        if not isinstance(payload, dict):
            raise ParserError("iQIYI Paopao API returned a non-object response")

        code = str(payload.get("code", ""))
        if code == NOT_FOUND_CODE:
            return "NULL", payload.get("msg") or "feed not found", row, None
        if code != SUCCESS_CODE:
            return "ERROR", payload.get("msg") or payload.get("data") or code, row, None

        feed = payload.get("data")
        if not isinstance(feed, dict):
            raise ParserError("iQIYI Paopao API response has an invalid data field")

        for field in FEED_FIELDS:
            value = feed.get(field)
            if field in LIST_FIELDS and isinstance(value, list):
                value = json.dumps(value, ensure_ascii=False)
            row[field] = value

        # Keep feedId derived from baseId, even if the response omits it.
        row["feedId"] = feed_id
        timestamp = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
        row["created_at"] = timestamp
        row["updated_at"] = timestamp

        return "OK", feed.get("name") or feed.get("feedTitle") or feed_id, row, None
