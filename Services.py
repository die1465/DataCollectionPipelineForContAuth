
from flask import Flask, request, jsonify
import sqlite3, threading, time, librosa, pandas as pd, os
from werkzeug.serving import run_simple
from AudioPreprocessingService import PreProcessAudio, PreProcessKeystrokeSensor
from ScrollingPreprocessingService import PreProcessScrollingData
from MouseMovementPreprocessingService import PreprocessMoveMovements
from DBConfig import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER, psycopg2

app = Flask(__name__)


@app.route('/process_keystroke_sensors', methods=['POST'])
def process_keystroke_sensors():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        session_id_from_request = data.get('session_id') # Renamed to avoid confusion with unpacked ID
        
        if not session_id_from_request:
            return jsonify({"error": "Session ID is required"}), 400
        
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # Step 2: Query the session data - SELECTING ONLY USED COLUMNS
        # Used: ID, DataFileName, StartKeyID, EndKeyID
        session_query = """
        SELECT "ID", "DataFileName", "StartKeyID", "EndKeyID"
        FROM "Sessions"
        WHERE "ID" = %s
        """
        cursor.execute(session_query, (session_id_from_request,))
        session_data = cursor.fetchone()

        if not session_data:
            raise ValueError(f"Session with ID {session_id_from_request} not found.")

        # Unpack only the 4 columns retrieved
        session_id_db, data_file_name, start_key_id, end_key_id = session_data
        
        # print(f"Session Data (partial): ID={session_id_db}, DataFileName={data_file_name}, StartKeyID={start_key_id}, EndKeyID={end_key_id}")

        # Load sensor data
        # Ensure 'data_file_name' points to the correct CSV file with the expected columns
        df = pd.read_csv(data_file_name, names=['sensor_type', 'timestamp', 'nanoTimestamp', 'x', 'y', 'z'])
        
        # Step 3: Query the keypress data for the session
        keypress_query = """
        SELECT "KeyDownTimestamp", "KeyUpTimestamp", "KeyPressed", "KeyID"
        FROM "KeyPresses"
        WHERE "KeyID" BETWEEN %s AND %s
        ORDER BY "KeyDownTimestamp"
        """
        cursor.execute(keypress_query, (start_key_id, end_key_id,))
        keypresses = cursor.fetchall()
        
        # Call the preprocessing function
        PreProcessKeystrokeSensor.save_keystroke_sensor(keypresses, df, session_id_db)

        return jsonify({
            "status": "success",
            "message": f"Sensor data for the keystrokes processed successfully for session {session_id_db}",
            "keystrokes_processed": len(keypresses),
            "output_directory": f"SessionsData/KeystrokeData/session_{session_id_db}"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()




@app.route('/process_audio', methods=['POST'])
def process_audio():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        session_id_from_request = data.get('session_id') # Renamed to avoid confusion with unpacked ID
        
        if not session_id_from_request:
            return jsonify({"error": "Session ID is required"}), 400
        
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # Step 2: Query the session data - SELECTING ONLY USED COLUMNS
        # Used: ID, DataFileName, StartKeyID, EndKeyID, BrowserOffset
        session_query = """
        SELECT "ID", "DataFileName", "StartKeyID", "EndKeyID", "BrowserOffset"
        FROM "Sessions"
        WHERE "ID" = %s
        """
        cursor.execute(session_query, (session_id_from_request,))
        session_data = cursor.fetchone()

        if session_data:
            # Unpack only the 5 columns retrieved
            session_id_db, data_file_name, start_key_id, end_key_id, browser_offset = session_data
            
            print(f"Session Data (partial): ID={session_id_db}, DataFileName={data_file_name}, StartKeyID={start_key_id}, EndKeyID={end_key_id}, BrowserOffset={browser_offset}")
        else:
            raise ValueError(f"Session with ID {session_id_from_request} not found.")

        
        # Step 3: Query the keypress data for the session
        keypress_query = """
        SELECT "KeyDownTimestamp", "KeyUpTimestamp", "KeyPressed", "KeyID"
        FROM "KeyPresses"
        WHERE "KeyID" BETWEEN %s AND %s
        ORDER BY "KeyDownTimestamp"
        """
        print(keypress_query)
        cursor.execute(keypress_query, (start_key_id, end_key_id,))
        keypresses = cursor.fetchall()

        # Ensure keypresses is not empty before accessing keypresses[0][0]
        if not keypresses:
            raise ValueError("No keypresses found for the given session ID range.")

        # Step 4: Load the audio file
        audio_path = f"{data_file_name}.wav" 
        y, sr = librosa.load(audio_path, sr=None)

        trim_ms = 80

        y_trimmed = PreProcessAudio.TrimAudioFromBeginning(y, trim_ms, sr)

        start_tone_ms, end_tone_ms = PreProcessAudio.detect_sync_tone(y_trimmed, sr, target_freq=18000, threshold_ratio=800.0)

        if start_tone_ms is None or end_tone_ms is None:
            raise RuntimeError("Could not detect sync tone. Cannot align keystrokes without it.")
        
        first_keypress_timestamp = keypresses[0][0] # Assuming first element of keypresses tuple is KeyDownTimestamp
        
        # Calculation for offset
        start_tone_browser_time = browser_offset - first_keypress_timestamp
        offset = start_tone_browser_time - start_tone_ms

        # aligning the keystroke timings with the audio file
        keypress_samples = PreProcessAudio.AdjustKeypressTimestamps(keypresses, first_keypress_timestamp + offset + trim_ms, y_trimmed, sr)
        
        # extracting and saving the keystroker data from the audio file
        # The db_path argument to save_keystroke_audio might need to be adjusted
        # if that function expects a direct DB connection or PostgreSQL details.
        # For now, it passes None as there's no direct DB path for psycopg2.
        PreProcessAudio.save_keystroke_audio(keypress_samples, y_trimmed, sr, session_id_db) # Pass session_id_db for consistency
        
        return jsonify({
            "status": "success",
            "message": f"Audio processed successfully for session {session_id_db}",
            "keystrokes_processed": len(keypress_samples),
            "output_directory": f"SessionsData/KeystrokeData/session_{session_id_db}"
        }), 200

    except Exception as e:
        print(e)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/process_scrolling', methods=['POST'])
def ProcessScrolling():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        session_id_from_request = data.get('session_id') # Renamed to avoid confusion with unpacked ID

        if not session_id_from_request:
            return jsonify({"error": "Session ID is required"}), 400
        
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # Step 2: Query the session data - ONLY SELECTING USED COLUMNS
        session_query = """
        SELECT "ID", "DataFileName", "StartScrollingID", "EndScrollingID"
        FROM "Sessions"
        WHERE "ID" = %s
        """
        cursor.execute(session_query, (session_id_from_request,))
        session_data = cursor.fetchone()

        if not session_data:
            raise ValueError(f"Session with ID {session_id_from_request} not found.")

        # Unpack only the 4 columns retrieved
        session_id, data_file_name, start_scroll_id, end_scroll_id = session_data
        
        print(f"Session Data (partial): {session_data}")
        
        # Load sensor data (assuming data_file_name points to the CSV)
        df = pd.read_csv(data_file_name, header=None, 
                        names=['sensor_type', 'timestamp', 'nanoTimestamp', 'x', 'y', 'z'])

        # Step 3: Query the scrolling data for the session
        scroll_query = """
        SELECT "StartTimestamp", "EndTimestamp", "Direction", "ID", "DataFileName"
        FROM "Scrolling"
        WHERE "ID" BETWEEN %s AND %s
        ORDER BY "StartTimestamp"
        """
        cursor.execute(scroll_query, (start_scroll_id, end_scroll_id,))
        scrolls = cursor.fetchall()
        scrollingDataPath = f"SessionsData/ScrollingData/"
        # ---- Segment and save each scroll event ----
        output_folder = f"{scrollingDataPath}session_{session_id}" # Using the ID retrieved from DB
        os.makedirs(output_folder, exist_ok=True)

        for start_ts_scroll, end_ts_scroll, direction, scroll_id_retrieved, _ in scrolls:
            segment = df[(df['timestamp'] >= start_ts_scroll) & (df['timestamp'] <= end_ts_scroll)]
            filename = f"{output_folder}/scroll_{scroll_id_retrieved}.csv"
            segment.to_csv(filename, index=False, header=False)

            # Update DataFileName column in Scrolling table
            update_query = """
            UPDATE "Scrolling"
            SET "DataFileName" = %s
            WHERE "ID" = %s
            """
            cursor.execute(update_query, (filename, scroll_id_retrieved))

        conn.commit()
        # conn.close()
        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400
        
        
        return jsonify({
        "status": "success",
        "message": f"scrolling processed successfully for session {session_id}",
        }), 200


    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/process_mouseMovement', methods=['POST'])
def ProcessMouseMovements():
    try:
        # Get session ID from request
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400
        
        PreprocessMoveMovements(session_id)
        
        
        return jsonify({
        "status": "success",
        "message": f"MouseMovements processed successfully for session {session_id}",
        }), 200


    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def run_flask_app():
    run_simple('localhost', 5050, app, use_reloader=False, use_debugger=True)

if __name__ == '__main__':
    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Keep the main thread alive
    while True:
        time.sleep(1)
