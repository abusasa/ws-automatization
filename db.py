import sqlite3
import csv
import os
import time

class Database:
    def __init__(self, db_name="whatsapp_state.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                phone TEXT PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                sent_at TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        self.conn.commit()

    def load_from_csv(self, csv_path):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Файл {csv_path} не найден.")

        cursor = self.conn.cursor()
        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != ['phone']:
                raise ValueError("CSV должен содержать один столбец: phone")

            for row in reader:
                phone = row['phone'].strip()
                if not phone:
                    continue
                cursor.execute('''
                    INSERT OR IGNORE INTO contacts (phone, status)
                    VALUES (?, 'pending')
                ''', (phone,))
        self.conn.commit()

    def get_pending_contact(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT phone FROM contacts WHERE status = 'pending' LIMIT 1")
        return cursor.fetchone()

    def mark_status(self, phone, status):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE contacts SET status = ?, sent_at = CURRENT_TIMESTAMP WHERE phone = ?
        ''', (status, phone))
        self.conn.commit()

    def get_start_time(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM meta WHERE key = 'start_time'")
        row = cursor.fetchone()
        if row:
            return float(row[0])
        else:
            current_time = time.time()
            cursor.execute("INSERT INTO meta (key, value) VALUES ('start_time', ?)", (str(current_time),))
            self.conn.commit()
            return current_time

    def get_stats(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM contacts GROUP BY status")
        return dict(cursor.fetchall())