#base.py

from sites.base import BaseParser, ParserError, retry
from .schema import SCHEMA
import hashlib

class Parser(BaseParser):

    name = "sina_kusou"
    schema = SCHEMA

    @retry(times=5)
    async def _fetch_data(self, vid, session, headers, row):

        row["vid"] = vid

        # http://image2.sina.com.cn/kusou/v/{vid后一位}/{vid后两位}/{vid后两位}/{vid}_(1|2|3|...).jpg

        i = 0
        image = []
        md5 = []
        blob = []

        """
        blob = [
            ("vid_0.jpg", bytes_0),
            ("vid_1.jpg", bytes_1),
            ...   
        ]
        """

        status = "NULL"
        while True:
            url = f"http://image2.sina.com.cn/kusou/v/{vid%10}/{vid%100}/{vid%100}/{vid}_{i}.jpg"

            async with session.get(
                url=url,
                headers=headers,
                timeout=60
            ) as r:
                #r.raise_for_status()
                if r.status == 200:
                    status = "OK"
                    data = await r.read()
                    image.append(f"{vid}_{i}.jpg")
                    md5.append(hashlib.md5(data).hexdigest())
                    blob.append((f"{vid}_{i}.jpg", data))
                    i += 1
                elif r.status == 404:
                    row["md5"] = None
                    break
                else:
                    # Only 404 marks the end of the image sequence. Other
                    # statuses must not leave the loop requesting the same URL.
                    r.raise_for_status()
                    raise ParserError(f"unexpected HTTP status {r.status} for image {i}")

        if status == "OK":
            row["image"] = ','.join(image)
            row["md5"] = ','.join(md5)
            return status, i, row, blob
        elif status == "NULL":
            return status, i, row, blob
