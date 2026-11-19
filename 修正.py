import json
import sqlite3

# ====== 在这里输入数据库文件名 ======
DB_FILE = "sina_02.db"
# ===================================

KEY_ORDER = ["file_id", "type", "size"]


def transform_videos(json_str: str) -> str:
    data = json.loads(json_str)
    if not isinstance(data, list):
        return json_str

    new_list = []
    for item in data:
        if not isinstance(item, dict):
            new_list.append(item)
            continue

        item.pop("definition", None)

        new_item = {}
        for k in KEY_ORDER:
            if k in item:
                new_item[k] = item[k]
        for k, v in item.items():
            if k not in new_item:
                new_item[k] = v

        new_list.append(new_item)

    # ensure_ascii=False -> 中文不转义
    # separators=(",", ":") -> 无空格（无 ", " 和 ": "）
    return json.dumps(new_list, ensure_ascii=False, separators=(",", ":"))


def main():
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute("SELECT rowid, videos FROM data WHERE videos IS NOT NULL")
        rows = cur.fetchall()
        print(f"待处理行数: {len(rows)}")

        updated = 0
        for rowid, videos in rows:
            try:
                new_videos = transform_videos(videos)
            except json.JSONDecodeError as e:
                print(f"[跳过] rowid={rowid} JSON 解析失败: {e}")
                continue
            if new_videos != videos:
                cur.execute(
                    "UPDATE data SET videos = ? WHERE rowid = ?",
                    (new_videos, rowid),
                )
                updated += 1

        conn.commit()
        print(f"已更新行数: {updated}")

        print("执行 VACUUM ...")
        cur.execute("VACUUM")
        print("VACUUM 完成。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
