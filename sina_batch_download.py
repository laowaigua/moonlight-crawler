# -*- coding: utf-8 -*-

import os
import subprocess
import sys

from core.searcher import Searcher


# ============================================================
# 配置
# ============================================================
SINADB_DIR = r".\data\sina"

# 下载器位置
DOWNLOADER = r"F:\sinadl\sinadl.py"


# ============================================================
# 生成TXT
# 格式：vid<TAB>video_id<TAB>title
# ============================================================
def gen_txt(db_list, field, start, end, extra_conditions, output_file):
    FIELDS = ["vid", "video_id", "title"]

    # 按字段类型拼范围条件：video_id 按字符串比较，vid 按数值比较
    if field == "video_id":
        range_cond = f'"{field}" >= \'{start}\' AND "{field}" <= \'{end}\''
    else:
        range_cond = f'"{field}" >= {start} AND "{field}" <= {end}'

    conditions = range_cond
    if extra_conditions:
        conditions += f' AND ({extra_conditions})'

    searcher = Searcher(db_list)
    count = 0

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        for row, source_db, source_table in searcher.run(
            keyword_list=None, fields=FIELDS, conditions=conditions
        ):
            vid = row[0]
            video_id = row[1]
            title = row[2]

            if vid is None:
                continue
            if video_id is None:
                video_id = ""
            if title is None:
                title = ""

            f.write(f"{vid}\t{video_id}\t{title}\n")
            count += 1

    print(f"生成TXT: {output_file}")
    print(f"数量: {count}")
    return count


# ============================================================
# 调用下载器
# ============================================================
def run_downloader(txt_file):
    downloader_dir = os.path.dirname(os.path.abspath(DOWNLOADER))

    cmd = [sys.executable, DOWNLOADER, "-i", txt_file]

    print()
    print("启动下载器")

    ok = False
    try:
        subprocess.run(cmd, cwd=downloader_dir, check=True)
        ok = True
    except subprocess.CalledProcessError as e:
        print(f"下载器异常退出: {e}")
    except FileNotFoundError as e:
        print(f"找不到下载器: {e}")
    finally:
        # 失败时保留 txt，方便重跑；成功才删除
        if ok and os.path.exists(txt_file):
            try:
                os.remove(txt_file)
                print(f"删除临时文件: {txt_file}")
            except Exception as e:
                print(f"删除失败: {e}")
        elif not ok and os.path.exists(txt_file):
            print(f"下载器未成功，保留临时文件: {txt_file}")


# ============================================================
# 输入
# ============================================================
def user_input():
    field_choice = input("请选择字段 (1=vid 2=video_id 默认2): ").strip()
    field = "vid" if field_choice == "1" else "video_id"
    default_mode = "2" if field_choice == "1" else "1"

    mode_choice = input(f"模式 (1=加减范围 2=指定范围 默认{default_mode}): ").strip()

    while True:
        if mode_choice not in ["1", "2", ""]:
            print("输入错误，请重新输入。")
            mode_choice = input(
                f"模式 (1=加减范围 2=指定范围 默认{default_mode}): "
            ).strip()
            continue

        if mode_choice == "":
            mode_choice = default_mode

        if mode_choice == "2":
            extra_conditions = None
            try:
                start_raw = input(f"请输入开始 {field}: ").strip()
                end_raw = input(f"请输入结束 {field}: ").strip()

                if field == "video_id":
                    # video_id 按字符串处理，避免大数溢出/前导零丢失
                    start = start_raw
                    end = end_raw
                else:
                    start = int(start_raw)
                    end = int(end_raw)

                c = input(
                    f"是否附带条件 video_id IS NULL (1=附带 0=不附带 默认0):  "
                ).strip()
                if c == "1":
                    extra_conditions = "video_id IS NULL"
            except ValueError:
                print("输入错误")
                return None

            name = f"{field}_{start}-{end}"
            break

        elif mode_choice == "1":
            extra_conditions = "1=1"
            try:
                if field == "video_id":
                    base_raw = input(f"请输入 {field}: ").strip()
                    base = base_raw
                    minus = input("减多少 默认50: ").strip()
                    plus = input("加多少 默认50: ").strip()
                    minus = int(minus) if minus else 50
                    plus = int(plus) if plus else 50
                    # 字符串无法做加减范围，退化为原值
                    start = base
                    end = base
                else:
                    base = int(input(f"请输入 {field}: "))
                    minus = input("减多少 默认50: ").strip()
                    plus = input("加多少 默认50: ").strip()
                    minus = int(minus) if minus else 50
                    plus = int(plus) if plus else 50
                    start = max(0, base - minus)
                    end = base + plus
            except ValueError:
                print("输入错误")
                return None

            name = f"{field}_{base}_-{minus}_+{plus}"
            break

    return field, start, end, name, extra_conditions


# ============================================================
# 主流程
# ============================================================
def main():
    result = user_input()
    if result is None:
        return

    field, start, end, name, extra_conditions = result

    db_list = []

    # vid 数据库分片
    if field == "vid":
        for i in range(start // 10000000, end // 10000000 + 1):
            db = f"{SINADB_DIR}\\sina_{i:02d}.db"
            if os.path.exists(db):
                db_list.append(db)
    # video_id 搜索全部数据库
    else:
        if os.path.isdir(SINADB_DIR):
            for f in os.listdir(SINADB_DIR):
                if f.endswith(".db"):
                    db_list.append(os.path.join(SINADB_DIR, f))

    if not db_list:
        print("没有找到数据库")
        return

    downloader_dir = os.path.dirname(os.path.abspath(DOWNLOADER))
    txt_file = os.path.join(downloader_dir, f"{name}.txt")

    print()
    print("开始搜索")
    print(f"数据库: {len(db_list)}")
    print(f"范围: {start}-{end}")

    cond = '"title" IS NULL'
    if extra_conditions:
        cond += f' AND ({extra_conditions})'

    count = gen_txt(db_list, field, start, end, cond, txt_file)

    if count == 0:
        print("没有匹配记录，跳过下载。")
        if os.path.exists(txt_file):
            try:
                os.remove(txt_file)
            except OSError:
                pass
        return

    run_downloader(txt_file)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断。")
    except Exception as e:
        print(f"\n程序发生错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            input("\n按回车退出...")
        except (EOFError, KeyboardInterrupt):
            pass
