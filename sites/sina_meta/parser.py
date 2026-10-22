# parser.py

from sites.base import BaseParser, ParserError, retry
from .schema import SCHEMA
from email.utils import parsedate_to_datetime
from datetime import timezone, timedelta

# http://s3.ivideo.sina.com.cn/{vid}.{ext}?meta&formatter=json

class Parser(BaseParser):

    name = "sina_meta"
    schema = SCHEMA

    @retry(times=5)
    async def _fetch_data(self, file_id, session, headers, row):

        row['file_id'] = file_id

        type = []
        Last_Modified = []
        Content_SHA1 = []
        Size = []
        Content_MD5 = []

        status = "NULL"

        for ext in ['flv', 'hlv', 'mp4']:

            #url = f"http://s3.ivideo.sina.com.cn/{file_id}.{ext}?meta&formatter=json"
            url = f"http://s3.ivideo.sina.com.cn.sinastorage.com/{file_id}.{ext}?meta&formatter=json"

            async with session.get(
                    url=url,
                    headers=headers,
                    timeout=60
            ) as r:
                #r.raise_for_status()
                if r.status == 200:
                    data = await r.json()
                    if not isinstance(data, dict):
                        raise ParserError(f"Sina metadata response for .{ext} is not an object")

                    try:
                        size = int(data["Size"])
                    except (KeyError, TypeError, ValueError, OverflowError) as exc:
                        raise ParserError(f"Sina metadata response for .{ext} has an invalid Size") from exc

                    if size > 0:
                        required_fields = ("Last-Modified", "Content-SHA1", "Content-MD5")
                        missing_fields = [field for field in required_fields if not data.get(field)]
                        if missing_fields:
                            raise ParserError(
                                f"Sina metadata response for .{ext} is missing: {', '.join(missing_fields)}"
                            )
                        status = "OK"
                        type.append(ext)
                        try:
                            Last_Modified.append(self._gmt_to_bj(data["Last-Modified"]))
                        except (TypeError, ValueError, OverflowError) as exc:
                            raise ParserError(f"Sina metadata response for .{ext} has an invalid Last-Modified") from exc
                        Content_SHA1.append(data["Content-SHA1"])
                        Size.append(size)
                        Content_MD5.append(data["Content-MD5"])
                    elif size == 0:
                        continue
                    else:
                        raise ParserError(f"Sina metadata response for .{ext} has a negative Size")
                elif r.status == 404:
                    continue
                else:
                    r.raise_for_status()

        if status == "OK":
            row["type"] = ",".join(type)
            row["Last-Modified"] = ",".join(Last_Modified)
            row["Content-SHA1"] = ",".join(Content_SHA1)
            row["Size"] = ",".join(map(str, Size))
            row["Content-MD5"] = ",".join(Content_MD5)
            return status, f"{row['type']}", row, None
        elif status == "NULL":
            return status, "404", row, None

    @staticmethod
    def _gmt_to_bj(s):

        dt_utc = parsedate_to_datetime(s)
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)

        # 转为北京时间（UTC+8）
        dt_bj = dt_utc.astimezone(timezone(timedelta(hours=8)))

        # 格式化输出
        result = dt_bj.strftime("%Y-%m-%d %H:%M:%S")

        return result  # 2012-08-17 06:34:23
