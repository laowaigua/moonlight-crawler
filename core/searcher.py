import sqlite3
from typing import List, Tuple
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import os

class Searcher:
    def __init__(self, db_list: List, max_workers = 5, print_status = True):
        self.db_list = db_list
        self.max_workers = max_workers
        self.print_status = print_status

    # ---------------- 核心搜索 ----------------

    def run(self, keyword_list=None, exclude_keyword_list=None, fields=None, conditions=None):
        q = Queue()
        workers = 0
        max_workers = min(self.max_workers, len(self.db_list))
        with ThreadPoolExecutor(max_workers = max_workers) as pool:
            for db in self.db_list:
                pool.submit(self._search_db, db, keyword_list, exclude_keyword_list, fields, conditions, q)
                workers += 1
            finished = 0

            while finished < workers:
                item = q.get()
                if item is None:
                    finished += 1
                    if self.print_status:
                        print(f" - {q.get()} 搜索完毕 ({finished}/{len(self.db_list)})")
                    continue
                yield item

    # ---------------- 内部方法 ----------------
    def _search_db(self, db, keyword_list, exclude_keyword_list, fields, conditions, q):
        if not os.path.exists(db):
            raise FileNotFoundError(f'文件 "{db}" 不存在。')
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA cache_size = 100000;")
        try:
            tables = self._get_tables(db)
            for table in tables:
                for row in self._search_table(conn=conn, table=table, keyword_list=keyword_list,
                                              exclude_keyword_list=exclude_keyword_list,
                                              fields=fields, conditions=conditions):
                    q.put((row, db, table))
        finally:
            conn.close()
            q.put(None)
            q.put(db)

    def _search_table(self, conn, table, keyword_list, exclude_keyword_list, fields, conditions, batch_size = 5000):
        t = time.time()
        #print(db, table, "START")
        try:
            cols = self._get_columns(conn, table)
            if keyword_list is None:
                where, params = "1=1", []
            else:
                where, params = self._build_where(keyword_list=keyword_list, exclude_keyword_list=exclude_keyword_list, fields=fields)
            if conditions:
                where += f" AND {conditions}"
            sql = f'SELECT * FROM "{table}" WHERE {where}'
            cur = conn.cursor()
            cur.execute(sql, params)

            while True:
                rows = cur.fetchmany(batch_size)
                #print(db, table, len(rows))
                if not rows:
                    #print(db, table, "END", time.time() - t)
                    break
                for row in rows:
                    yield row
        except Exception as e:
            print(f"{e}")

    @staticmethod
    def _get_tables(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cur.fetchall()]
        except Exception:
            tables = []
        finally:
            conn.close()
        return tables

    @staticmethod
    def _get_columns(conn, table):
        cur = conn.cursor()
        cur.execute(f'PRAGMA table_info("{table}")')
        return {r[1] for r in cur.fetchall()}

    @staticmethod
    def _build_where(keyword_list: List, exclude_keyword_list: List, fields: List[str]) -> Tuple[str, List]:
        """
        构建 SQLite WHERE 子句和参数列表

        排除逻辑：
        - [[REASON, SEASON]]：排除同时包含 REASON 和 SEASON（组内用 OR）
        - [[REASON], [SEASON]]：排除包含 REASON 或 SEASON（组间用 AND）
        """
        if not fields:
            raise ValueError("fields cannot be empty")

        all_conditions = []
        params = []

        # ========== 1. 处理包含关键词（组内 OR，组间 AND）==========
        if keyword_list is not None and isinstance(keyword_list, list) and keyword_list:
            include_groups = []
            for keyword_group in keyword_list:
                if not keyword_group:
                    continue
                like_conditions = []
                for field in fields:
                    for keyword in keyword_group:
                        like_conditions.append(f"{field} LIKE ?")
                        params.append(f"%{keyword}%")
                if like_conditions:
                    include_groups.append("(" + " OR ".join(like_conditions) + ")")
            if include_groups:
                all_conditions.append(" AND ".join(include_groups))

        # ========== 2. 处理排除关键词 ==========
        if exclude_keyword_list is not None and isinstance(exclude_keyword_list, list) and exclude_keyword_list:
            exclude_groups = []

            for exclude_group in exclude_keyword_list:
                if not isinstance(exclude_group, list):
                    exclude_group = [exclude_group]

                keywords = [k for k in exclude_group if k]
                if not keywords:
                    continue

                # ✅ 关键修改：组内用 OR（同一组的关键词是"或"关系）
                group_conditions = []
                for keyword in keywords:
                    field_conditions = []
                    for field in fields:
                        field_conditions.append(f"IFNULL({field}, '') NOT LIKE ?") # 防止NULL值
                        params.append(f"%{keyword}%")
                    # 同一关键词的多字段用 AND
                    group_conditions.append("(" + " AND ".join(field_conditions) + ")")

                # 组内用 OR：匹配任一关键词就排除
                if group_conditions:
                    exclude_groups.append("(" + " OR ".join(group_conditions) + ")")

            # 组间用 AND：必须满足所有排除组
            if exclude_groups:
                all_conditions.append(" AND ".join(exclude_groups))

        # ========== 3. 组合所有条件 ==========
        if all_conditions:
            #print((" AND ".join(all_conditions), params))
            return " AND ".join(all_conditions), params
        return "1=1", []

def gen_db_list(file, dir, recursive_dir):

    db_list = []

    if dir is None and recursive_dir is None and file is None:
        dir = ['.']

    if dir is not None:
        for l in dir:
            for d in l:
                if not os.path.isdir(d):
                    print(f'[Warning] 目录 "{d}" 不存在。')
                    continue
                db_list.extend(
                    os.path.join(d, f)
                    for f in os.listdir(d)
                    if f.endswith(".db")
                )

    if recursive_dir is not None:
        for l in recursive_dir:
            for d in l:
                if not os.path.isdir(d):
                    print(f'[Warning] 目录 "{d}" 不存在。')
                    continue
                db_list.extend(
                    os.path.join(root, f)
                    for root, dirs, files in os.walk(d)
                    for f in files if f.endswith(".db")
                )

    if file is not None:
        for l in file:
            for f in l:
                if not os.path.isfile(f):
                    print(f'[Warning] 文件 "{f}" 不存在。')
                    continue
                db_list.append(f)

    #print(db_list)
    return db_list
