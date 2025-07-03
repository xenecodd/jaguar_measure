from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.query import Query
from datetime import datetime
import json
import sqlite3
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class AppwriteDataWriter:
    def __init__(self):
        load_dotenv()
        self.client = Client()
        self.client.set_endpoint("http://192.168.1.22:8880/v1")
        self.client.set_project("68643fcb0001cf502505")
        self.client.set_key(os.getenv("APPWRITE_API_KEY"))
        self.db = Databases(self.client)
        self.database_id = "6864f41e0004c15584a3"
        self.collection_id = "68650d63001c49d92663"
        self._ensure_attributes()

    def _ensure_attributes(self):
        attributes = [
            ("date", "string", 20),
            ("iteration", "integer", None),
            ("group_number", "integer", None),
            ("feature", "string", 255),
            ("value", "double", None)
        ]
        for key, attr_type, size in attributes:
            try:
                if attr_type == "string":
                    self.db.create_string_attribute(
                        self.database_id, 
                        self.collection_id, 
                        key=key, 
                        size=size, 
                        required=False
                    )
                elif attr_type == "integer":
                    self.db.create_integer_attribute(
                        self.database_id, 
                        self.collection_id, 
                        key=key, 
                        required=False
                    )
                elif attr_type == "double":
                    self.db.create_float_attribute(
                        self.database_id, 
                        self.collection_id, 
                        key=key, 
                        required=False
                    )
            except Exception as e:
                if "already exists" not in str(e):
                    print(f"Attribute oluşturulurken hata ({key}): {str(e)}")

    def is_appwrite_available(self) -> bool:
        try:
            self.db.list_documents(
                database_id=self.database_id,
                collection_id=self.collection_id,
                queries=[Query.limit(1)]
            )
            return True
        except Exception as e:
            logger.error(f"Appwrite bağlantı hatası: {e}")
            return False

    def write_to_sqlite(self, result, iteration, group_number):
        conn = sqlite3.connect("local_buffer.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buffered_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                iteration INTEGER,
                group_number INTEGER,
                feature TEXT,
                value REAL
            )
        """)
        for feature, raw_value in result.items():
            try:
                value = float(raw_value)
            except (ValueError, TypeError):
                value = None
            cursor.execute("""
                INSERT INTO buffered_results (date, iteration, group_number, feature, value)
                VALUES (DATE('now'), ?, ?, ?, ?)
            """, (iteration, group_number, feature, value))
        conn.commit()
        conn.close()

    def get_current_group_info(self):
        try:
            max_group_result = self.db.list_documents(
                database_id=self.database_id,
                collection_id=self.collection_id,
                queries=[
                    Query.order_desc("group_number"),
                    Query.limit(1)
                ]
            )
            current_group = 0
            if max_group_result['documents']:
                current_group = max_group_result['documents'][0]['group_number']
            group_results = self.db.list_documents(
                database_id=self.database_id,
                collection_id=self.collection_id,
                queries=[
                    Query.equal("group_number", current_group),
                    Query.limit(1000)
                ]
            )
            group_indices = set()
            for doc in group_results['documents']:
                group_indices.add(doc['iteration'])
            return current_group, group_indices
        except Exception as e:
            logger.error(f"Grup bilgisi alınırken hata: {e}")
            return 0, set()

    def flush_sqlite_to_appwrite(self):
        try:
            conn = sqlite3.connect("local_buffer.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM buffered_results")
            buffered_data = cursor.fetchall()
            if not buffered_data:
                conn.close()
                return
            for row in buffered_data:
                _, date, iteration, group_number, feature, value = row
                document_data = {
                    "date": date,
                    "iteration": iteration,
                    "group_number": group_number,
                    "feature": feature,
                    "value": value
                }
                try:
                    self.db.create_document(
                        database_id=self.database_id,
                        collection_id=self.collection_id,
                        document_id="unique()",
                        data=document_data
                    )
                except Exception as e:
                    logger.error(f"Buffered veri Appwrite'a yazılırken hata: {e}")
                    continue
            cursor.execute("DELETE FROM buffered_results")
            conn.commit()
            conn.close()
            logger.info(f"{len(buffered_data)} buffered veri Appwrite'a aktarıldı")
        except Exception as e:
            logger.error(f"SQLite'dan Appwrite'a flush hatası: {e}")

    def write_to_db(self, result: dict, iteration: int, group_number: int):
        try:
            self.flush_sqlite_to_appwrite()
            for feature_name, raw_value in result.items():
                try:
                    value_float = float(raw_value)
                except (ValueError, TypeError):
                    value_float = None
                document_data = {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "iteration": iteration,
                    "group_number": group_number,
                    "feature": feature_name,
                    "value": value_float
                }
                try:
                    self.db.create_document(
                        database_id=self.database_id,
                        collection_id=self.collection_id,
                        document_id="unique()",
                        data=document_data
                    )
                except Exception as e:
                    logger.error(f"Appwrite'a yazım hatası: {e}")
                    self.write_to_sqlite({feature_name: raw_value}, iteration, group_number)
        except Exception as e:
            logger.error(f"Appwrite yazım hatası: {e}")
            self.write_to_sqlite(result, iteration, group_number)

    def create_document(self, data, document_id=None):
        try:
            result = self.db.create_document(
                database_id=self.database_id,
                collection_id=self.collection_id,
                document_id=document_id or "unique()",
                data=data
            )
            print(f"Belge başarıyla oluşturuldu: {result['$id']}")
            return result
        except Exception as e:
            print(f"Belge oluşturulurken hata: {str(e)}")
            return None

    def update_document(self, document_id, data):
        try:
            result = self.db.update_document(
                database_id=self.database_id,
                collection_id=self.collection_id,
                document_id=document_id,
                data=data
            )
            print(f"Belge başarıyla güncellendi: {document_id}")
            return result
        except Exception as e:
            print(f"Belge güncellenirken hata: {str(e)}")
            return None

    def create_multiple_documents(self, data_list):
        results = []
        for i, data in enumerate(data_list):
            result = self.create_document(data)
            if result:
                results.append(result)
                print(f"Belge {i+1}/{len(data_list)} oluşturuldu")
            else:
                print(f"Belge {i+1}/{len(data_list)} oluşturulamadı")
        return results

    def upsert_document(self, document_id, data):
        try:
            result = self.update_document(document_id, data)
            if result:
                return result
        except Exception:
            pass
        try:
            return self.create_document(data, document_id)
        except Exception as e:
            print(f"Upsert işlemi başarısız: {str(e)}")
            return None
