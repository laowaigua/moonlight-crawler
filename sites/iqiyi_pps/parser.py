"""Parser for the iQIYI video base-info API."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sites.base import BaseParser, ParserError, retry
from .schema import SCHEMA


API_URL = "https://pcw-api.iqiyi.com/video/video/baseinfos/{ids}"
SUCCESS_CODE = "A00000"
BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def _format_timestamp(value):
    """Convert the API's seconds or millisecond timestamp to Beijing time."""
    try:
        timestamp = int(value)
        if timestamp <= 0:
            return None
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OverflowError, OSError):
        return None


class Parser(BaseParser):
    name = "iqiyi_pps"
    schema = SCHEMA

    @retry(times=5)
    async def _fetch_data(self, item, session, headers, row):
        try:
            base = int(item)
        except (TypeError, ValueError):
            raise ParserError(f"invalid iQIYI base id: {item!r}")

        # The crawler input is the base number. iQIYI's tvId appends the
        # two-digit source suffix (09 = PPS) after multiplying the base by 100.
        tv_id = base * 100 + 9

        row["baseId"] = base
        row["tvId"] = tv_id
        async with session.get(
            API_URL.format(ids=tv_id),
            headers={**headers, "Referer": "https://www.iqiyi.com/"},
            timeout=60,
        ) as response:
            response.raise_for_status()
            payload = await response.json()

        if not isinstance(payload, dict):
            raise ParserError("iQIYI API returned a non-object response")

        if payload.get("code") != SUCCESS_CODE:
            return "NULL", payload.get("errMsg") or payload.get("data"), row, None

        data = payload.get("data")
        if isinstance(data, dict):
            # The endpoint normally returns a list; tolerate a single record too.
            data = [data]
        if not isinstance(data, list):
            raise ParserError("iQIYI API response has an invalid data field")

        video = next(
            (entry for entry in data
             if isinstance(entry, dict) and str(entry.get("tvId")) == str(tv_id)),
            None,
        )
        if video is None:
            return "NULL", "video not found", row, None

        user = video.get("user")
        user_id = video.get("userId")
        if user_id is None and isinstance(user, dict):
            user_id = user.get("id")

        row.update({
            "title": video.get("name") or "",
            "description": video.get("description") or "",
            "publish_time": _format_timestamp(video.get("publishTime")),
            "albumId": video.get("albumId"),
            "image": video.get("imageUrl") or "",
            "user_id": user_id,
            "duration": video.get("duration"),
            "play_url": video.get("playUrl") or "",
            "effective": 1 if video.get("effective") else 0,
            "page_publish_state": video.get("pagePublishStatus") or "",
        })
        return "OK", row["title"], row, None
