import sqlite3
import os
import logging
from config import Config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_name = Config.DATABASE_NAME
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)
    
    def init_db(self):
        try:
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
            logger.info("✅ Database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    def add_user(self, user_id, username, first_name, last_name):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def add_file(self, user_id, file_id, file_name, file_type, file_size, description=None):
        try:
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
        except Exception as e:
            logger.error(f"Error adding file: {e}")
            return None
    
    def get_user_files(self, user_id):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, file_name, file_type, file_size, upload_date, description
                FROM files WHERE user_id = ? ORDER BY upload_date DESC
            ''', (user_id,))
            
            files = cursor.fetchall()
            conn.close()
            return files
        except Exception as e:
            logger.error(f"Error getting user files: {e}")
            return []
    
    def get_file(self, file_db_id, user_id):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT file_id, file_name, file_type FROM files 
                WHERE id = ? AND user_id = ?
            ''', (file_db_id, user_id))
            
            file_data = cursor.fetchone()
            conn.close()
            return file_data
        except Exception as e:
            logger.error(f"Error getting file: {e}")
            return None
    
    def delete_file(self, file_db_id, user_id):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM files WHERE id = ? AND user_id = ?
            ''', (file_db_id, user_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def get_file_stats(self, user_id):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*), SUM(file_size) FROM files WHERE user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()
            conn.close()
            return stats
        except Exception as e:
            logger.error(f"Error getting file stats: {e}")
            return (0, 0)
