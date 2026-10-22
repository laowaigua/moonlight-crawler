# base.py

SCHEMA = {
    "video_id": "INTEGER PRIMARY KEY ASC",
    "title": "TEXT",
    "duration": "REAL",
    "state": "TEXT", # update: 判断视频是否可以申诉恢复
    "created": "TEXT", # update: 判断视频来自优酷还是土豆
    "published": "TEXT",
    "description": "TEXT",
    "public_type": "TEXT", # update: 判断视频是否为加密或私有
    "user_id": "INTEGER",
    "tags": "TEXT",
}