import mysql.connector
from datetime import datetime, date
import json
from pathlib import Path
import sys
import logging

logger = logging.getLogger(__name__)

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent))
from config import Config as config

class ScanDatabaseService:
    def __init__(self):
        self.connection_config = {
            'host': config.DB_HOST,
            'user': config.DB_USER,
            'password': config.DB_PASSWORD,
            'database': config.DB_NAME,
            'charset': 'utf8mb4'
        }
    
    def get_connection(self):
        """Create and return database connection"""
        return mysql.connector.connect(**self.connection_config)
    
    def get_available_dates(self):
        """Get list of available dates in database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT DISTINCT date 
                FROM scan_results 
                ORDER BY date DESC
            """
            
            cursor.execute(query)
            dates = [row[0].strftime('%Y-%m-%d') for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return dates
            
        except Exception as e:
            print(f"Error getting available dates: {e}")
            return []
    
    def get_scan_data_by_date_range(self, start_date, end_date):
        """Get scan data for a specific date range"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT date, iteration, feature, value
                FROM scan_results 
                WHERE date BETWEEN %s AND %s
                ORDER BY date ASC, iteration ASC, feature ASC
            """
            
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            
            cursor.close()
            conn.close()
            logger.error(f"Retrieved {len(rows)} rows from database for date range {start_date} to {end_date}")
            return self._convert_db_rows_to_json_format(rows)
            
        except Exception as e:
            print(f"Error getting scan data: {e}")
            return []
    
    def get_scan_data_by_date(self, target_date):
        """Get scan data for a specific date"""
        return self.get_scan_data_by_date_range(target_date, target_date)
    
    def _convert_db_rows_to_json_format(self, rows):
        """Convert database rows to the format expected by generate_json_data()"""
        # Group by date and iteration
        grouped_data = {}
        
        for row in rows:
            scan_date, iteration, feature, value = row
            date_key = scan_date.strftime('%Y-%m-%d')
            
            if date_key not in grouped_data:
                grouped_data[date_key] = {}
            
            if iteration not in grouped_data[date_key]:
                grouped_data[date_key][iteration] = {
                    'Index': iteration,
                    'date': date_key
                }
            
            # Add feature value to the iteration
            grouped_data[date_key][iteration][feature] = value
        
        # Convert to list format similar to JSON file format
        all_results = []
        for date_key in sorted(grouped_data.keys()):
            for iteration in sorted(grouped_data[date_key].keys()):
                all_results.append(grouped_data[date_key][iteration])
        
        return all_results