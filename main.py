import sqlite3
import os
from config import Config

class Database:
    def __init__(self):
        self.db_name = Config.DATABASE_NAME
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, first_name, last_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()
    
    def add_file(self, user_id, file_id, file_name, file_type, file_size, description=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO files (user_id, file_id, file_name, file_type, file_size, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, file_id, file_name, file_type, file_size, description))
        
        file_db_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return file_db_id
    
    def get_user_files(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, file_name, file_type, file_size, upload_date, description
            FROM files WHERE user_id = ? ORDER BY upload_date DESC
        ''', (user_id,))
        
        files = cursor.fetchall()
        conn.close()
        return files
    
    def get_file(self, file_db_id, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT file_id, file_name, file_type FROM files 
            WHERE id = ? AND user_id = ?
        ''', (file_db_id, user_id))
        
        file_data = cursor.fetchone()
        conn.close()
        return file_data
    
    def delete_file(self, file_db_id, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM files WHERE id = ? AND user_id = ?
        ''', (file_db_id, user_id))
        
        conn.commit()
        conn.close()
    
    def get_file_stats(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*), SUM(file_size) FROM files WHERE user_id = ?
        ''', (user_id,))
        
        stats = cursor.fetchone()
        conn.close()
        return stats
