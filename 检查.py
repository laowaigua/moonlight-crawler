import json
import re
import sqlite3

# ====== 在这里输入数据库文件名 ======
DB_FILE = "sina_02.db"
# ===================================

# 严格要求的键顺序
EXPECTED_KEYS = ["file_id", "type", "size", "md5"]


def check_value(json_str: str):
    """返回 (ok: bool, reason: str)。ok=True 表示完全符合目标格式。"""
    # 1. 严格无空格检查：对象内不应出现 ", " 或 ": "（字符串值内部除外不易区分，
    #    这里先做序列化对比，序列化结果一致即视为无多余空格）
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return False, f"JSON 解析失败: {e}"

    if not isinstance(data, list):
        return False, f"顶层不是数组，而是 {type(data).__name__}"

    if len(data) == 0:
        return False, "空数组 []"

    # 2. 逐元素校验键集合与顺序
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            return False, f"第 {i} 个元素不是对象，而是 {type(item).__name__}"
        keys = list(item.keys())
        if keys != EXPECTED_KEYS:
            return False, f"第 {i} 个元素键为 {keys}，期望 {EXPECTED_KEYS}"
        for k in EXPECTED_KEYS:
            if not isinstance(item[k], str):
                return False, (
                    f"第 {i} 个元素 {k} 类型为 {type(item[k]).__name__}，期望 str"
                )

    # 3. 严格无空格：用与写入时相同的序列化参数比对
    canonical = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if canonical != json_str:
        return False, "存在多余空格或非规范序列化（与实际存储文本不一致）"

    return True, ""


def main():
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute("SELECT rowid, videos FROM data WHERE videos IS NOT NULL")
        rows = cur.fetchall()
        print(f"总行数（videos 非空）: {len(rows)}")

        bad = 0
        for rowid, videos in rows:
            ok, reason = check_value(videos)
            if not ok:
                bad += 1
                print(f"[不符合] rowid={rowid}: {reason}")
                # 可打印片段辅助定位（避免刷屏，截断）
                preview = videos if len(videos) <= 200 else videos[:200] + "..."
                print(f"         内容: {preview}")

        if bad == 0:
            print("✔ 全部符合格式 file_id, type, size, md5（无空格、无 definition）")
        else:
            print(f"✘ 共 {bad} 行不符合，{len(rows) - bad} 行符合")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
