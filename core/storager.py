# storager.py
import os
import sqlite3
import asyncio
from pathlib import Path
import time
import hashlib

class Storager:

    def __init__(self, db, schema, table, conflict="IGNORE", batch_size=1000, auto_vacuum=True):
        self.db = db
        self.schema = schema
        self.table = table
        self.conflict = conflict
        self.batch_size = batch_size
        self.auto_vacuum = auto_vacuum

        self.init_time = time.time_ns()
        self.digit = hashlib.md5(f"{self.db}:{self.init_time}".encode( "utf-8", errors="ignore")).hexdigest()[:8]
        print(f"[Storager] 存储器创建成功 id:{self.digit}")

        self.queue = asyncio.Queue()
        self._writer_task = None
        self._stop_writer = asyncio.Event()

        # 建表
        print("[Storager] Accessing database file...")
        Path(self.db).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db, check_same_thread=False)
        cur = self.conn.cursor()
        create_sql = self.gen_create_sql(self.schema, table)
        cur.execute(create_sql)
        self.conn.commit()

    def gen_create_sql(self, schema, table):
        cols = ", ".join([f'"{col}" {typ}' for col, typ in schema.items()])
        return f'CREATE TABLE IF NOT EXISTS "{table}" ({cols})'

    async def start_writer(self):
        """启动数据库写入协程"""
        #print("WRITER START")
        if self._writer_task is None:
            self._writer_task = asyncio.create_task(self._db_writer())

    async def stop_writer(self):
        """停止写入并 flush 剩余队列"""
        self._stop_writer.set()
        if self._writer_task:
            await self._writer_task
            self._writer_task = None
        if self.auto_vacuum:
            self.conn.execute("VACUUM")
            self.conn.commit()
        self.conn.close()

    async def save_row(self, row, blob):
        """爬虫协程只需放入队列即可"""
        await self.queue.put((row, blob))

    async def _db_writer(self):
        """单独写入协程"""
        #print("WRITER LOOP ENTER")
        batch = []
        while not self._stop_writer.is_set() or not self.queue.empty():
            try:
                row, blob = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                if row:
                    batch.append((row, blob))
            except asyncio.TimeoutError:
                pass

            # 满 batch 或停止事件触发时 flush
            if len(batch) >= self.batch_size or (self._stop_writer.is_set() and batch):
                await self._flush_batch(batch)
                batch.clear()

    async def _flush_batch(self, batch):
        """批量写入数据库，带锁重试"""
        #print(batch)
        if not batch:
            return

        cur = self.conn.cursor()
        keys = list(batch[0][0].keys())
        placeholders = ','.join(['?'] * len(keys))
        columns = ','.join(f'"{k}"' for k in keys)

        primary_key = self._get_primary_key()

        if self.conflict == 'IGNORE':
            sql = f'INSERT OR IGNORE INTO "{self.table}" ({columns}) VALUES ({placeholders})'
        elif self.conflict == 'UPDATE':
            update_clause = ', '.join(
                f'{k} = COALESCE("{self.table}".{k}, excluded.{k})'
                for k in keys if k != primary_key
            )
            sql = f'''INSERT INTO "{self.table}" ({columns})
                        VALUES ({placeholders})
                        ON CONFLICT({primary_key}) DO UPDATE SET
                        {update_clause}
                        '''
        elif self.conflict == 'REPLACE':
            update_clause = ', '.join(
                f'{k} = excluded.{k}'
                for k in keys if k != primary_key
            )
            sql = f'''INSERT INTO "{self.table}" ({columns})
            VALUES ({placeholders})
            ON CONFLICT({primary_key}) DO UPDATE SET
            {update_clause}
            '''
            #print(sql)

        values = [tuple(r[0][k] for k in keys) for r in batch]

        max_retries = 5
        for attempt in range(max_retries):
            try:
                cur.executemany(sql, values)
                self.conn.commit()
                break
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    await asyncio.sleep(0.05)
                else:
                    raise

        files = [x for r in batch if r[1] for x in r[1]]

        if files:
            os.makedirs(f"{os.path.join(os.path.dirname(self.db), f'{self.db}_files')}", exist_ok=True)

            for filename, data in files:
                with open(os.path.join(f"{self.db}_files", filename), 'wb') as f:
                    f.write(data)


    def _get_primary_key(self):
        for c in self.schema.items():
            if "PRIMARY" in c[1].upper():
                return c[0]
        return None

    async def record_error(self, item, error_info):
        with open(f"{self.db}_errors_{self.digit}.txt", "a", encoding="utf-8") as f:
            f.write(f"{item} {error_info}\n")

    def close(self):
        self.conn.close()
