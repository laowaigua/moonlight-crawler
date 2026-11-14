# schema.py

SCHEMA = {
    "vid": "INTEGER PRIMARY KEY ASC",
    "video_id": "INTEGER",
    "title": "TEXT",
    "length": "INTEGER",
    "description": "TEXT",
    "create_time": "TEXT", # UTC+8
    "videos": "TEXT", # {["file_id": ,"size": ,"type": ], [], ...}
    "message": "TEXT", # OK | 视频已删除(deleted) | 视频审核不通过(failed to pass the review) | 该视频不存在(not found)
}
