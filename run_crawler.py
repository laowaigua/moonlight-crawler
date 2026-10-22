# run_crawler.py

import argparse
from core.crawler import Crawler
from core.storager import Storager
import time
import asyncio
import sites.loader

def main():

    parser = argparse.ArgumentParser("Crawler")
    parser.add_argument("site", choices=sites.loader.list_site(), help="要运行的站点爬虫名称")
    parser.add_argument("-s", "--start", type=int, help="ID 范围起点；未使用 --input 时必填")
    parser.add_argument("-e", "--end", type=int, help="ID 范围终点；未使用 --input 时必填")
    parser.add_argument(
        "--step", type=int, default=None,
        help="ID 步长；省略时根据范围方向自动选择（start < end 为 1，start > end 为 -1）",
    )
    parser.add_argument("-i", "--input", type=str, help="从文本文件逐行读取 ID；每行首个字段必须是整数")
    parser.add_argument("-o", "--output", type=str, help="输出 SQLite 数据库路径；默认 ./<站点>_<start>-<end>.db")
    parser.add_argument("-t", "--table", default="data", help="数据库表名（默认：data）")
    parser.add_argument("--crawler-chunk-size", type=int, default=100_000, help="每个处理分块包含的 ID 数量（默认：100000）")
    parser.add_argument("--crawler-concurrency", type=int, default=8, help="同时处理的请求数（默认：8）")
    parser.add_argument("--crawler-delay", type=int, default=100, help="每个请求启动前的延迟，单位毫秒（默认：100）")
    parser.add_argument(
        "--session-max-items", type=int, default=0,
        help="处理指定数量的条目后重建 HTTP session；0 表示整次运行复用同一个 session（默认：200）",
    )
    parser.add_argument("--storager-batch-size", type=int, default=500, help="每批写入数据库的记录数（默认：500）")
    parser.add_argument(
        "--conflict", type=str, choices=['IGNORE','REPLACE'], default='IGNORE',
        help="主键冲突策略：IGNORE 忽略重复记录，REPLACE 用新记录替换（默认：IGNORE）",
    )

    args = parser.parse_args()

    if args.input:
        items = []
        with open(args.input, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    items.append(int(line.split()[0]))
                except (ValueError, IndexError):
                    print(f"[Warning] 输入文件第 {line_number} 行不是有效整数，已跳过：{line.rstrip()!r}")
        if args.output is None:
            if items:
                start = args.start if args.start is not None else min(items)
                end = args.end if args.end is not None else max(items)
            else:
                start = args.start if args.start is not None else 0
                end = args.end if args.end is not None else 0
            args.output = f"./{args.site}_{start}-{end}.db"
    else:
        if args.start is None or args.end is None:
            parser.error("未使用 --input 时，必须提供 --start 和 --end")
        step_was_default = args.step is None
        if step_was_default:
            args.step = 1 if args.start < args.end else -1
        elif args.step == 0:
            parser.error("--step 不能为 0")
        if args.output is None:
            args.output = f"./{args.site}_{args.start}-{args.end}.db"

    site_parser = sites.loader.load_parser(args.site)()
    site_schema = sites.loader.load_schema(args.site)

    storager = Storager(args.output, site_schema, args.table, args.conflict, batch_size=args.storager_batch_size)
    crawler = Crawler(
        site_parser,
        storager,
        chunk_size=args.crawler_chunk_size,
        concurrency=args.crawler_concurrency,
        delay=args.crawler_delay,
        session_max_items=args.session_max_items,
    )
    #crawler.print_settings["NULL"] = False

    if not args.input:
        items = range(args.start, args.end, args.step)

    #print(items)

    start_time = time.time()
    asyncio.run(crawler.run(items)) ###
    end_time = time.time()

    count = len(items)
    elapsed = end_time - start_time
    rate = count / elapsed if elapsed > 0 else 0

    print(f"[Crawler] All done ({elapsed:.2f}s {rate:.2f}vids/s).")

if __name__ == "__main__":
    main()
