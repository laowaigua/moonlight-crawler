import base64
import xml.etree.ElementTree as ET
from urllib.parse import unquote

from sites.base import BaseParser, retry
from .schema import SCHEMA


class Parser(BaseParser):

    name = "xuite"
    schema = SCHEMA

    CDX_API = "https://web.archive.org/cdx/search/cdx"
    SNAPSHOT_ROOT = "https://web.archive.org/web/"
    PLAYER_URL = "https://vlog.xuite.net/flash/player"

    @retry(times=5)
    async def _fetch_data(self, vid, session, headers, row):
        row["id"] = vid
        media_id = base64.b64encode(str(vid).encode("utf-8")).decode("ascii")
        original_url = f"{self.PLAYER_URL}?media={media_id}"

        params = [
            ("url", original_url),
            ("output", "json"),
            ("filter", "statuscode:200"),
            ("fl", "timestamp,original,statuscode,mimetype"),
            ("collapse", "digest"),
            ("limit", "100"),
        ]
        async with session.get(
            self.CDX_API, params=params, headers=headers, timeout=60
        ) as response:
            response.raise_for_status()
            rows = await response.json(content_type=None)

        if not isinstance(rows, list) or len(rows) < 2:
            return "NULL", "没有找到 200 状态的 Wayback 存档", row, None

        columns = rows[0]
        snapshots = [dict(zip(columns, record)) for record in rows[1:]]
        snapshots = [item for item in snapshots if item.get("timestamp")]
        if not snapshots:
            return "NULL", "没有找到 200 状态的 Wayback 存档", row, None

        snapshot = max(snapshots, key=lambda item: item["timestamp"])
        timestamp = snapshot["timestamp"]
        archived_url = f"{self.SNAPSHOT_ROOT}{timestamp}id_/{original_url}"
        row["archive"] = f"{self.SNAPSHOT_ROOT}{timestamp}/{original_url}"

        async with session.get(archived_url, headers=headers, timeout=60) as response:
            if response.status == 404:
                return "NULL", f"存档内容不存在（{timestamp}）", row, None
            response.raise_for_status()
            body = await response.text(errors="replace")

        self._parse_metadata(body, row)
        return "OK", row["title"] or timestamp, row, None

    @staticmethod
    def _parse_metadata(body, row):
        """Decode Xuite's XML properties, whose names and values are Base64."""
        root = ET.fromstring(body)
        properties = {}

        for prop in root.findall("./property"):
            encoded_name = prop.get("id")
            encoded_value = prop.text
            if not encoded_name or not encoded_value:
                continue
            try:
                name = base64.b64decode(encoded_name).decode("utf-8")
                value = base64.b64decode(encoded_value).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                continue
            properties[name] = unquote(value)

        row["title"] = properties.get("title") or None
        row["description"] = properties.get("description") or None
        row["duration"] = properties.get("duration") or None
        # Xuite's ``category`` is a broad classification (e.g. 個人短片),
        # not a video's tags. Keep this field for explicit tag/keyword data only.
        row["tag"] = (
            properties.get("tag")
            or properties.get("tags")
            or properties.get("keywords")
            or None
        )
        row["publish_datetime"] = properties.get("publish_datetime") or None
        row["author_id"] = properties.get("author_id") or None

        if row["duration"] is not None:
            try:
                row["duration"] = float(row["duration"])
            except (TypeError, ValueError):
                row["duration"] = None
