#base.py

from sites.base import BaseParser, retry
from .schema import SCHEMA
from datetime import datetime
from zoneinfo import ZoneInfo

class Parser(BaseParser):

    name = "sina"
    schema = SCHEMA

    @retry(times=5)
    async def _fetch_data(self, vid, session, headers, row):

        row["vid"] = vid
        
        # 通过vid获取video_id
        async with session.get(
            "https://s.video.sina.com.cn/video/getvideoidbyvid",
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
            '''
            async with session.get(
                    "http://api.ivideo.sina.com.cn/public/video/play",
                    headers = headers,
                    params = {
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
            '''
            async with session.get(
                    "https://s.video.sina.com.cn/video/play",
                    headers=headers,
                    params={"video_id": video_id},
                    timeout=60
            ) as r:
                r.raise_for_status()
                data = await r.json()

            if not isinstance(data, dict):
                return "ERROR", "Sina video lookup returned a non-object response", row, None

            if data.get("code") == 0:
                status = 'OK'
                return status, data.get("message"), row, None
            elif data.get("code") == 1:
                video_data = data.get("data")
                if not isinstance(video_data, dict):
                    return "ERROR", "Sina video response is missing a valid data object", row, None

                status = 'OK'
                row["title"] = video_data.get("title")
                row["length"] = video_data.get("length")
                row["description"] = video_data.get("description")

                create_time = video_data.get("create_time") if video_data.get("create_time") \
                    else await self._get_create_time_from_api(session, headers, video_id)

                try:
                    row["create_time"] = self._ts_to_beijing(int(create_time)) if create_time else None
                except (TypeError, ValueError, OverflowError, OSError):
                    row["create_time"] = None

                return status, row["title"], row, None

            return "ERROR", data.get("message"), row, None

        return "ERROR", data.get("message"), row, None

    def _ts_to_beijing(self, ts: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        BJ_TZ = ZoneInfo("Asia/Shanghai")
        return datetime.fromtimestamp(ts, BJ_TZ).strftime(fmt)

    async def _get_create_time_from_api(self, session, headers, video_id):
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
            return None
        video_data = data.get("data")
        return video_data.get("create_time") if isinstance(video_data, dict) else None
