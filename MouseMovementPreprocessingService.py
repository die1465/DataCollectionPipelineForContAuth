import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import uuid
import os
from dataclasses import dataclass
from typing import List, Tuple, Optional
from DBConfig import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER, psycopg2

@dataclass
class MouseMovement:
    id: int
    start_time: float
    end_time: float
    direction: str

def process_session( session_id: int): # Changed session_id to int, common for IDs
    conn = None
    cursor = None
    try:
        # Step 1: Connect to the PostgreSQL database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # Query Session data
        # Using double quotes for table and column names for PostgreSQL
        # Using %s as the parameter placeholder for psycopg2
        cursor.execute("""
        SELECT "StartTimestamp", "EndTimestamp", "DataFileName", "StartMouseMovementID", "EndMouseMovementID"
        FROM "Sessions"
        WHERE "ID" = %s""", (session_id,)) 
        
        session_data = cursor.fetchone()

        if not session_data:
            raise ValueError(f"Session with ID {session_id} not found.")

        start_timestamp_db, end_timestamp_db, data_file_name, start_mouse_id, end_mouse_id = session_data

        # Get mouse data
        # Using double quotes for table and column names for PostgreSQL
        # Using %s as the parameter placeholder for psycopg2
        cursor.execute("""
            SELECT "StartTimestamp", "EndTimestamp", "Direction", "ID", "DataFileName"
            FROM "MouseMovement"
            WHERE "ID" BETWEEN %s AND %s 
            ORDER BY "StartTimestamp" """, (start_mouse_id, end_mouse_id)) 
        
        mouse_movements = cursor.fetchall()
        
        # Load sensor data
        # Assuming data_file_name refers to the actual sensor data CSV for the session
        # Ensure the number of 'names' matches the columns in your CSV
        df = pd.read_csv(data_file_name, header=None,
                        names=['timestamp', 'x', 'y', 'z']) 
        output_dir = "SessionsData/MouseMovementData/"
        # Ensure output folder exists
        output_folder = f"{output_dir}session_{session_id}"
        os.makedirs(output_folder, exist_ok=True)

        # Iterate through mouse movements
        for start_ts, end_ts, direction, mouse_id, _ in mouse_movements: # The '_' is for DataFileName from the SELECT
            # Extract corresponding segment
            segment = df[(df['timestamp'] >= start_ts) & (df['timestamp'] <= end_ts)]
            
            # Save to file without header
            filename = f"{output_folder}/mouse_{mouse_id}.csv"
            segment.to_csv(filename, index=False, header=False)

            # Update database with filename
            # Using double quotes for table and column names for PostgreSQL
            # Using %s as the parameter placeholder for psycopg2
            cursor.execute("""
                UPDATE "MouseMovement"
                SET "DataFileName" = %s
                WHERE "ID" = %s
            """, (filename, mouse_id)) 

        # Commit all changes and close the connection
        conn.commit()
        print(f"Mouse movements processed and updated for session {session_id}")

    except psycopg2.Error as e:
        # Rollback changes if a database-specific error occurs
        if conn:
            conn.rollback() 
        print(f"Database error processing session {session_id}: {e}")
        raise # Re-raise the exception after handling
    except Exception as e:
        # Catch other unexpected errors
        print(f"An unexpected error occurred processing session {session_id}: {e}")
        raise # Re-raise other exceptions
    finally:
        # Ensure cursor and connection are always closed
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def PreprocessMoveMovements(session_id: str):
    """Entry point for processing a session"""
    
    process_session(session_id)



