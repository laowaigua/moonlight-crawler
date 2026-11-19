# -*- coding: utf-8 -*-

import os
import subprocess
import sys

from core.searcher import Searcher


# ============================================================
# 配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SINADB_DIR = os.path.join(BASE_DIR, "data", "sina")

# 下载器位置
DOWNLOADER = r"F:\sinadl\sinadl.py"


# ============================================================
# 生成TXT
# 格式：vid<TAB>video_id<TAB>title
# ============================================================
def gen_txt(db_list, field, start, end, extra_conditions, output_file):
    FIELDS = ["vid", "video_id", "title"]

    conditions = f'"{field}" >= {start} AND "{field}" <= {end}'
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
    field = "vid"

    mode_choice = input("模式 (1=加减范围 2=指定范围 默认1): ").strip()

    if mode_choice == "2":
        try:
            start = int(input(f"请输入开始 {field}: "))
            end = int(input(f"请输入结束 {field}: "))
        except ValueError:
            print("输入错误")
            return None

        name = f"{field}_{start}-{end}"
        base = start  # 模式2也定义一个基准值，供"与vid相同"奇偶判断使用

    else:
        try:
            base = int(input(f"请输入 {field}: "))

            minus = input("减多少 默认0: ").strip()
            plus = input("加多少 默认500: ").strip()

            minus = int(minus) if minus else 0
            plus = int(plus) if plus else 500
        except ValueError:
            print("输入错误")
            return None

        start = max(0, base - minus)
        end = base + plus

        name = f"{field}_{base}_-{minus}_+{plus}"

    # 奇偶选择：循环直到拿到合法值
    while True:
        parity_choice = input(
            f"vid奇偶 (0=与{field}相同 1=奇数 2=偶数 n=不限制 默认0): "
        ).strip()

        if parity_choice == "" or parity_choice == "0":
            parity_choice = "1" if base % 2 == 1 else "2"

        if parity_choice == "1":
            parity_condition = "vid % 2 = 1"
            parity_name = "奇"
        elif parity_choice == "2":
            parity_condition = "vid % 2 = 0"
            parity_name = "偶"
        elif parity_choice == "n":
            parity_condition = "1=1"
            parity_name = "全"
        else:
            print("输入错误，请重新输入。")
            continue

        break

    name = f"{name}_{parity_name}"

    return field, start, end, name, parity_condition


# ============================================================
# 主流程
# ============================================================
def main():
    result = user_input()

    if result is None:
        return

    field, start, end, name, parity_condition = result

    db_list = []

    # vid 数据库分片
    if field == "vid":
        for i in range(start // 10000000, end // 10000000 + 1):
            db = os.path.join(SINADB_DIR, f"sina_{i:02d}.db")
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
    print(f"奇偶筛选: {parity_condition}")

    extra_conditions = (
        f'"title" IS NULL AND "video_id" IS NULL '
        f'AND {parity_condition}'
    )

    count = gen_txt(db_list, field, start, end, extra_conditions, txt_file)

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
