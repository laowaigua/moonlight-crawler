# schema.py

from..sina.schema import SCHEMA as SINA_SCHEMA

SCHEMA = {
    "vid": "INTEGER PRIMARY KEY ASC",
    "video_id": "INTEGER",
    "title": "TEXT",
    "length": "INTEGER",
    "mp4vid": "INTEGER"
}