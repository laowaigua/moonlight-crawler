# parser.py

from sites.base import BaseParser, retry
from .schema import SCHEMA

class Parser(BaseParser):

    name = "sina_ipad_vid"
    schema = SCHEMA

    @retry(times=5)
    async def _fetch_data(self, vid, session, headers, row):

        row["vid"] = vid

        # 通过vid获取video_id
        async with session.get(
            "https://s.video.sina.com.cn/Video/getvideoidbyvid",
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

            # 通过接口获取视频ipad_vid
            async with session.get(
                    "http://video.sina.com.cn/interface/video_ids/video_ids.php",
                    headers=headers,
                    params={"v": str(vid)},
                    timeout=60
            ) as r:
                r.raise_for_status()
                data = await r.json()

            if not isinstance(data, dict):
                return "ERROR", "Sina ID lookup returned a non-object response", row, None

            if data.get("ipad_vid") == False:
                status = 'NULL'
                return status, data.get("message"), row, None
            elif isinstance(data.get("ipad_vid"), str):
                status = 'OK'
                row["ipad_vid"] = int(data.get("ipad_vid"))
                return status, data.get("ipad_vid"), row, None

        return "ERROR", data.get("message"), row, None
