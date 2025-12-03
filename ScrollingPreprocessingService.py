import pandas as pd
import sqlite3
import uuid
from datetime import datetime
from typing import List, Tuple

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        return self.conn.cursor()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

class SensorDataProcessor:
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.df = None
        self.sensor_start = None
        self.sensor_end = None
        
    def load_and_preprocess(self):
        """Load and preprocess sensor data"""
        self.df = pd.read_csv(self.data_file, header=None,
                            names=['timestamp', 'accel_x', 'accel_y', 'accel_z',
                                   'gyro_x', 'gyro_y', 'gyro_z'])
        self._convert_timestamps()
        return self
    
    def _convert_timestamps(self):
        """Convert sensor timestamps to datetime objects"""
        self.df['datetime'] = pd.to_datetime(self.df['timestamp'], unit='ms')
        self.sensor_start = self.df['datetime'].iloc[0]
        self.sensor_end = self.df['datetime'].iloc[-1]
        self.df['rel_time'] = (self.df['datetime'] - self.sensor_start).dt.total_seconds()

class ScrollDataHandler:
    def __init__(self, scrolls: List[Tuple], session_start_db: datetime):
        self.scrolls = scrolls
        self.session_start_db = session_start_db
        self.scrolls_datetime = []
        
    def convert_scroll_timestamps(self):
        """Convert raw scroll timestamps to datetime objects"""
        self.scrolls_datetime = [
            (s[0],  # ID
             pd.to_datetime(s[1], unit='ms'),  # Start time
             pd.to_datetime(s[2], unit='ms'),  # End time
             s[3]   # Direction
            ) for s in self.scrolls
        ]
        return self

class TimeAligner:
    def __init__(self, scrolls_datetime: List[Tuple], sensor_start: datetime, sensor_end: datetime):
        self.scrolls_datetime = scrolls_datetime
        self.sensor_start = sensor_start
        self.sensor_end = sensor_end
        self.time_shift = None
        
    def calculate_alignment(self):
        """Calculate time alignment between scroll events and sensor data"""
        first_scroll_start = self.scrolls_datetime[0][1]
        last_scroll_end = self.scrolls_datetime[-1][2]
        
        expected_duration = (last_scroll_end - first_scroll_start).total_seconds() + 1
        actual_duration = (self.sensor_end - self.sensor_start).total_seconds()
        self.time_shift = expected_duration - actual_duration
        return self

class ScrollDataExporter:
    def __init__(self, df: pd.DataFrame, time_shift: float):
        self.df = df
        self.time_shift = time_shift
        
    def process_and_export(self, scrolls_datetime: List[Tuple], cursor: sqlite3.Cursor):
        """Process and export scroll data to individual files"""
        first_scroll_start = scrolls_datetime[0][1]
        scrolls_relative = []
        
        for scroll_id, start_db, end_db, direction in scrolls_datetime:
            start_rel, end_rel = self._calculate_relative_times(start_db, end_db, first_scroll_start)
            
            if not self._validate_time_range(start_rel, end_rel):
                continue
                
            self._export_scroll_data(scroll_id, start_rel, end_rel, cursor)
            scrolls_relative.append((scroll_id, start_rel, end_rel, direction))
            
        return scrolls_relative
    
    def _calculate_relative_times(self, start_db: datetime, end_db: datetime, first_scroll_start: datetime):
        """Calculate relative times adjusted for sensor alignment"""
        start_rel = (start_db - first_scroll_start).total_seconds() - self.time_shift
        end_rel = (end_db - first_scroll_start).total_seconds() - self.time_shift
        return max(start_rel, 0), max(end_rel, 0)
    
    def _validate_time_range(self, start: float, end: float) -> bool:
        """Validate the calculated time range"""
        return not (start == 0 and end == 0)
    
    def _export_scroll_data(self, scroll_id: int, start_rel: float, end_rel: float, cursor: sqlite3.Cursor):
        """Export individual scroll data to CSV and update database"""
        mask = (self.df['rel_time'] >= start_rel) & (self.df['rel_time'] <= end_rel)
        scroll_data = self.df[mask]
        
        if scroll_data.empty:
            print(f"No data found for scroll {scroll_id}")
            return
        
        filename = f"SessionsData/ScrollingData/scroll_{scroll_id}_{uuid.uuid4()}_data.csv"
        scroll_data.to_csv(filename, index=False)
        
        cursor.execute("""
            UPDATE Scrolling 
            SET DataFileName = ? 
            WHERE ID = ?""", (filename, scroll_id))
        # print(f"Saved scroll {scroll_id} data to {filename}")

# Main execution flow
def PreProcessScrollingData(session_id: str) -> bool:
    """Main execution flow with proper error handling"""
    try:
        db_path = "DataCollection.db"
        
        # Database operations
        with DatabaseManager(db_path) as cursor:
            # Get session data
            cursor.execute("""
                SELECT StartTimestamp, EndTimestamp, DataFileName, StartScrollingID, EndScrollingID 
                FROM Sessions WHERE ID = ?""", (session_id,))
            session_data = cursor.fetchone()
            
            if not session_data:
                raise ValueError(f"Session {session_id} not found")
                
            start_timestamp_db, end_timestamp_db, data_file_name, start_scroll_id, end_scroll_id = session_data
            
            # Get scroll data
            cursor.execute("""
                SELECT ID, StartTimestamp, ENDTimestamp, Direction 
                FROM Scrolling WHERE ID BETWEEN ? AND ? 
                ORDER BY StartTimestamp""", (start_scroll_id, end_scroll_id))
            scrolls = cursor.fetchall()
        
        # Process sensor data
        data_processor = SensorDataProcessor(data_file_name)
        data_processor.load_and_preprocess()
        
        # Process scroll data
        scroll_handler = ScrollDataHandler(scrolls, pd.to_datetime(start_timestamp_db, unit='ms'))
        scroll_handler.convert_scroll_timestamps()
        
        # Calculate time alignment
        aligner = TimeAligner(
            scroll_handler.scrolls_datetime,
            data_processor.sensor_start,
            data_processor.sensor_end
        )
        aligner.calculate_alignment()
        
        # Export scroll data
        with DatabaseManager(db_path) as cursor:
            exporter = ScrollDataExporter(data_processor.df, aligner.time_shift)
            exporter.process_and_export(scroll_handler.scrolls_datetime, cursor)
            
        return True
    
    except sqlite3.Error as e:
        print(f"Database error occurred: {str(e)}")
        return False
    except FileNotFoundError as e:
        print(f"File error occurred: {str(e)}")
        return False
    except pd.errors.ParserError as e:
        print(f"CSV parsing error: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    PreProcessScrollingData("105")