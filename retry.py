# repairer.py
import argparse
import asyncio
import sqlite3
from pathlib import Path
from core.crawler import Crawler
from core.storager import Storager
from core.searcher import gen_db_list
import sites.loader

# ---------------- 配置 ----------------
TABLE = "data"       # 表名
SQL = {
    "youku":{
        "select": "video_id",
        "where": '"title" IS NULL'
    },
    "youku_new":{
        "select": "video_id",
        "where": '"title" IS NOT NULL'
    },
    "sina":{
        "select": "vid",
        "where": '"title" IS NULL'
    },
    "sina_api":{
        "select": "vid",
        "where": '"title" IS NULL'
    },
    "sina_wap":{
        "select": "vid",
        "where": '"title" IS NULL'
    },
    "sina_meta":{
        "select": "file_id",
        "where": '"type" IS NULL'
    },
    "sina_kusou":{
        "select": "vid",
        "where": '"md5" IS NULL'
    },
    "sohu":{
        "select": "vid",
        "where": '"title" IS NULL'
    }
    "iqiyi_pps":{
        "select": "baseId",
        "where": '"title" IS NULL'
    }
}

# ---------------- 工具函数 ----------------
def iter_db_files(directory):
    """遍历目录下所有 .db 文件"""
    for path in Path(directory).rglob("*.db"):
        yield path

def find_bad_vids(site, db_file, table, condition=None):
    """从单个数据库中找出疑似错误的 video_id"""
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    select = SQL[site]["select"]
    where = f'{SQL[site]["where"]} AND ({condition})' if condition else SQL[site]["where"]
    sql = f'SELECT {select} FROM "{table}" WHERE {where}'
    try:
        cur.execute(sql)
        vids = [row[0] for row in cur.fetchall()]
    except sqlite3.Error as e:
        print(f"[WARN] {db_file}: {e}")
        vids = []
    conn.close()
    return vids

# ---------------- 主流程 ----------------
async def repair_db(site, db_file, table, condition, crawler_concurrency, storager_batch_size):
    print(f"[Retry] Processing {db_file} ...")
    vids = find_bad_vids(site, db_file, table, condition)
    if not vids:
        print(f"[Retry] No bad vids found in {db_file}.")
        return

    print(f"[Retry] {len(vids)} vids to retry in {db_file}")

    schema = sites.loader.load_schema(site)
    parser = sites.loader.load_parser(site)()

    storage = Storager(db=db_file, schema=schema, table=table, conflict="UPDATE", batch_size=storager_batch_size)

    crawler = Crawler(parser, storage, concurrency=crawler_concurrency)
    crawler.print_settings["NULL"] = False # 只输出 OK 和 ERROR
    crawler.storage_settings["NULL"] = False

    await crawler.run(vids)

async def main():

    args = argparse.ArgumentParser("Crawler")
    args.add_argument("site", choices=sites.loader.list_site())
    args.add_argument("-d", "--dir", type=str, nargs="+", action="append")
    args.add_argument("-D", "--recursive-dir", type=str, nargs="+", action="append")
    args.add_argument("-f", "--file", nargs="+", action="append")
    args.add_argument("-t", "--table", default="data")
    args.add_argument("-c", "--condition", type=str)
    args.add_argument("--crawler-concurrency", type=int, default=16)
    args.add_argument("--storager-batch-size", type=int, default=1)

    args = args.parse_args()

    site = args.site

    db_list = gen_db_list(args.file, args.dir, args.recursive_dir)
    for db_file in db_list:
        await repair_db(site, db_file, args.table, args.condition, crawler_concurrency=args.crawler_concurrency,
        storager_batch_size=args.storager_batch_size)

if __name__ == "__main__":
    asyncio.run(main())
