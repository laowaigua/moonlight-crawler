# base.py
import json

from sites.base import BaseParser, retry
from .schema import SCHEMA
from datetime import datetime
from zoneinfo import ZoneInfo
import re

class Parser(BaseParser):
    name = "sina"
    schema = SCHEMA

    @retry(times=5)
    async def _fetch_data(self, vid, session, headers, row):

        row["vid"] = vid

        # 通过vid获取video_id
        async with session.get(
                "http://s.video.sina.com.cn/Video/getvideoidbyvid",
                headers=headers,
                params={"vid": str(vid)},
                timeout=60
        ) as r:
            r.raise_for_status()
            data = await r.json()

        if not isinstance(data, dict):
            return "ERROR", "Sina ID lookup returned a non-object response", row, None

        if data.get("code") == 0:
            status = 'NULL'
            return status, data.get("message"), row, None
        elif data.get("code") == 1:
            lookup_data = data.get("data")
            if not isinstance(lookup_data, dict):
                return "ERROR", "Sina ID lookup response is missing a valid data object", row, None
            video_id = lookup_data.get("video_id")
            if video_id is None:
                return "ERROR", "Sina ID lookup response is missing video_id", row, None
            row["video_id"] = video_id
        # 通过video_id获取视频信息

        async with session.get(
                "http://s.video.sina.com.cn/Video/play",
                headers=headers,
                params={
                    "video_id": video_id
                },
                timeout=60
        ) as r:
            r.raise_for_status()
            data = await r.json()

        if not isinstance(data, dict):
            return "ERROR", "Sina video lookup returned a non-object response", row, None

        message = data.get("message")

        if message == "OK":

            video_data = data.get("data")
            if not isinstance(video_data, dict):
                return "ERROR", "Sina video response is missing a valid data object", row, None

            status = 'OK'

            row["title"] = video_data.get("title")
            row["length"] = video_data.get("length")
            row["description"] = video_data.get("description")
            create_time = video_data.get("create_time")
            try:
                row["create_time"] = self._ts_to_beijing(int(create_time)) if create_time else None
            except (TypeError, ValueError, OverflowError, OSError):
                row["create_time"] = None
            videos_list = video_data.get("videos")
            videos = []
            for v in videos_list:
                videos.append(
                    {
                        "file_id": v.get("file_id"),
                        "size": v.get("size"),
                        "type": v.get("type"),
                        "md5": v.get("md5")
                    }
                )
            row["videos"] = json.dumps(videos, separators=(',', ':'), ensure_ascii=False)
            row["message"] = message

            return status, row["title"], row, None

        elif "review" in message or "deleted" in message or "transcode" in message or "not found" in message:

            status = 'OK'

            row["message"] = message.split("(")[1].split(")")[0]

            return status, row["message"], row, None

        return "ERROR", data.get("message"), row, None

    @staticmethod
    def _ts_to_beijing(self, ts: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        BJ_TZ = ZoneInfo("Asia/Shanghai")
        return datetime.fromtimestamp(ts, BJ_TZ).strftime(fmt)
