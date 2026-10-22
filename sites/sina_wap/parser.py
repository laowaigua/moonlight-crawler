# parser.py

from sites.base import BaseParser, retry
from .schema import SCHEMA

class Parser(BaseParser):

    name = "sina_wap"
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

            # 通过wap接口获取视频信息
            url = "https://interface.sina.cn/video/wap/videoinfo.d.json"
            async with session.get(
                    url,
                    headers = headers,
                    params = {
                        "vid": vid
                    },
                    timeout=60
            ) as r:
                r.raise_for_status()
                data = await r.json()

            if not isinstance(data, dict):
                return "ERROR", "Sina WAP lookup returned a non-object response", row, None
            video_data = data.get("data")
            if data.get("code") == 1 and not isinstance(video_data, dict):
                return "ERROR", "Sina WAP response is missing a valid data object", row, None

            if data.get("code") == 1 and video_data.get("title") is not None:
                status = 'OK'
                row["title"] = video_data.get("title")
                row["length"] = video_data.get("timeLength")
                row["description"] = None # wap接口返回值全为""
                row["create_time"] = None

                return status, row["title"], row, None
            elif data.get("code") == 1:
                status = 'NULL'
                return status, data.get("message") or "video title is missing", row, None

            return "ERROR", data.get("message"), row, None

        return "ERROR", data.get("message"), row, None
