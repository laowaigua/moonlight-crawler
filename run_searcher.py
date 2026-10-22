# run_searcher.py

import argparse
import sites.loader
from core.searcher import Searcher
from core.searcher import gen_db_list
import re
import sqlite3
from datetime import datetime
from pathlib import Path
import time
import os

_DEFAULT_FIELDS = {
    "youku":["title","description","tags"],
    "sina":["title","description"],
    "sina_wap":["title"],
    "sohu":["title","keywords","description"],
    "youtube":["title"]
}

def safe_filename(s):
    s = re.sub(r"[\"']", "", s)
    s = re.sub(r'[\\/:*?<>|]', '-', s)
    return s

def link_list(l, char='_', suffix=""):
    #print(l)
    return char.join(p for p in l if p) + f"{suffix}"

def gen_output(args):

    format_dict = {
        "sites": args.site,
        "time": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "keyword": args.keyword,
        "exclude_keyword": args.exclude_keyword,
        "conditions": args.conditions if args.conditions else ""
    }
    #print(format_dict)

    default_filename = safe_filename(
        link_list(
            [
                format_dict["time"],
                f"{format_dict['keyword']}" if format_dict["keyword"] else None,
                f"x{format_dict['exclude_keyword']}" if format_dict["exclude_keyword"] else None,
                format_dict["sites"],
                f"({format_dict['conditions']})" if format_dict["conditions"] else None
            ],
            suffix = ".db"
        )
    )

    # 没传 --output
    if not args.output:
        output = Path("search") / default_filename
        return output

    output_path = Path(link_list((s % format_dict for s in args.output), suffix=".db")) if len(args.output) > 1 else Path(args.output[0] % format_dict)

    # 已存在目录 或 不存在，但像目录（无后缀）
    if (output_path.exists() and output_path.is_dir()) or (not output_path.exists() and not output_path.suffix):
        return Path(output_path / default_filename)

    # 明确是文件
    return output_path

def main():
    t = time.time()
    parser = argparse.ArgumentParser("Searcher")
    parser.add_argument("site", choices=sites.loader.list_schema())
    parser.add_argument("-d", "--dir", type=str, nargs="+", action="append")
    parser.add_argument("-D", "--recursive-dir", type=str, nargs="+", action="append")
    parser.add_argument("-f", "--file", nargs="+", action="append")
    parser.add_argument("-k", "--keyword", type=str, nargs="+", action="append", default=None)
    parser.add_argument("-x", "--exclude-keyword", type=str, nargs="+", action="append", default=None)
    parser.add_argument("-F", "--fields", nargs="+", default=None)
    parser.add_argument("-c", "--conditions", type=str, default=None)
    parser.add_argument("-o", "--output", type=str, nargs="+", default=None)
    parser.add_argument("-t", "--table", type=str, default="results")
    parser.add_argument("--record-source", action="store_true")
    parser.add_argument("--max-workers", type=int, default=5)

    args = parser.parse_args()

    db_files = gen_db_list(args.file, args.dir, args.recursive_dir)
    print(f"[Searcher] 开始搜索共 {len(db_files)} 个文件...")

    searcher = Searcher(db_list=db_files, max_workers=args.max_workers)

    output = gen_output(args)

    fields = args.fields if args.fields else _DEFAULT_FIELDS[args.site]

    # --- 保存阶段 ---

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(output)
    cur = conn.cursor()

    table = args.table
    schema = sites.loader.load_schema(args.site)
    if args.record_source:
        schema["source"] = "TEXT"
    cols = ", ".join([f'"{col}" {typ}' for col, typ in schema.items()])
    cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({cols})')

    count = 0
    for row, source_db, source_table in searcher.run(keyword_list=args.keyword, exclude_keyword_list=args.exclude_keyword, fields=fields, conditions=args.conditions):
        if args.record_source:
            source = f"{source_db}-{source_table}"
            row += (source, )
        cur.execute(f'INSERT INTO "{table}" VALUES ({",".join(["?"] * len(row))})', row)
        count += 1

    conn.commit()
    conn.execute("VACUUM;")
    conn.close()

    elapsed_time = time.time() - t
    print(f"[Searcher] 搜索到 {count} 条记录，已保存至：{output}（用时 {elapsed_time:.2f} 秒）。")

if __name__ == "__main__":
    main()
