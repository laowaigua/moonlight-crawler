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
                        #"definition": v.get("definition"),
                        "file_id": v.get("file_id"),
                        "type": v.get("type"),
                        "size": v.get("size"),
                        "md5": v.get("md5")
                    }
                )
            row["videos"] = json.dumps(videos, separators=(',', ':'), ensure_ascii=False)
            row["message"] = message

            return status, row["title"], row, None

        elif "review" in message or "transcode" in message:

            status = 'OK'
            async with session.get(
                    "http://api.ivideo.sina.com.cn/public/video/play",
                    headers=headers,
                    params={
                        "appname": "sinaplayer_pc",
                        "tags": "sinaplayer_pc",
                        "applt": "web",
                        "appver": "V11220.210521.03",
                        "player": "all",
                        "video_id": video_id
                    },
                    timeout=60
            ) as r:
                r.raise_for_status()
                data = await r.json()

            if not isinstance(data, dict):
                return "ERROR", "Sina video lookup returned a non-object response", row, None

            message = data.get("Message")
            if "review" in message or "transcode" in message:

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

                row["videos"] = None
                row["message"] = message.split("(")[1].split(")")[0]

                return status, row["title"], row, None

        elif "deleted" in message \
             or "not found"  in message \
             or "offline" in message \
             or "transcoding" in message :

            status = 'OK'
            row["message"] = message.split("(")[1].split(")")[0] \
                if "transcoding" not in message \
                else "transcoding"

            return status, row["message"], row, None

        return "ERROR", data.get("message"), row, None

    @staticmethod
    def _ts_to_beijing(ts: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        BJ_TZ = ZoneInfo("Asia/Shanghai")
        return datetime.fromtimestamp(ts, BJ_TZ).strftime(fmt)
