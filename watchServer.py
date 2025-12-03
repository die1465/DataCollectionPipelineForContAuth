import socketio, eventlet, base64, logging
from pydub import AudioSegment
from ServiceCalls import process_audio_threaded, process_scrolling_threaded, process_mouseMovement_threaded, process_keystroke_sensors_threaded
from watchUtils import *
import time
#from models import Sessions

# Create a Socket.IO server
sio = socketio.Server(async_mode='eventlet')
flaskApp = Flask(__name__)


def isNotValidWatchConnection():
    global watchSID
    if watchSID == 0:
        return True
    return False
#todo remove the up and down from scrolling, only make it record scrolling data

# Event handler for client connections
@sio.event
def connect(sid, environ):
    global websiteSID, watchSID, audioServiceSID, sensorServiceSID
    print(f"Client connected: {sid}")
    deviceType = environ.get("HTTP_DEVICE_TYPE")
    if deviceType == "website":
        print("website connected")
        websiteSID = sid
    elif deviceType == "MainWatchConnection":
        print("watch connected")
        watchSID = sid
    elif deviceType == "AudioService":
        print("audio service connected")
        audioServiceSID = sid
    elif deviceType == "SensorService":
        print("sensor service connected")
        sensorServiceSID = sid

# Event handler for client disconnections
@sio.event
def disconnect(sid):
    global watchSID, websiteSID
    if sid == watchSID:
        watchSID = 0 
    else:
        websiteSID = 0
    print(f"Client disconnected: {sid}")

# Event handler for custom events
@sio.event
def message(sid, data):
    print(f"Received message from {sid}: {data}")
    
    # Send a response back to the client
    response = f"Server received: {data}"
    sio.emit("message", response, to=sid)
    print(f"Sent response to {sid}: {response}")

@sio.event
def RecordAllActivities(sid, data):
    #record all sensor and audio data
    clsActivityRecorder.startRecordingActivity(data)


@sio.event
def StopRecordingActivity(sid, data):
    clsActivityRecorder.stopRecordingActivity(data)

@sio.event
def DoneStreamingActivityAudioData(sid, data):
    clsActivityRecorder.handleStoppingActivityAudioRecording(data)

@flaskApp.route('/uploadActivityAudioPCM', methods=['POST'])
def uploadActivityPCM():
    # ensure output directory exists
    
    full_path = os.path.join(clsActivityRecorder.ActivitySessionsPath, clsActivityRecorder.AudioOutputPath)

    try:
        # open in append-binary mode
        with open(full_path, 'ab') as f:
            # request.stream is a file-like wrapper over the WSGI input
            chunk_size = 4096
            while True:
                chunk = request.stream.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        app.logger.error(f"Failed writing PCM chunk: {e}")
        abort(500)
    
    return ('', 204)


@flaskApp.route("/api/AllActivitySensorStream", methods=["POST"])
def AllActivitySensorStream():
    global typingSessionsPath, keyStrokeSensorOutputFile

    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400

        uploaded_file = request.files["file"]

        if uploaded_file.filename == "":
            return jsonify({"status": "error", "message": "Empty filename"}), 400

        full_path = os.path.join(clsActivityRecorder.ActivitySessionsPath, 
                      clsActivityRecorder.SensorOutputPath)

        # Save the raw file content (only CSV data, no headers)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        uploaded_file.save(full_path)

        clsActivityRecorder.HandleStoppingAllActivitySensorRecording()

        return jsonify({"status": "success", "message": f"File saved as {keyStrokeSensorOutputFile}"}), 200

    except Exception as e:
        print(f"Error handling file upload: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@sio.event
def AllActivitySensorStream(sid, data):
    clsActivityRecorder.allActivitySensorStream(data)


@sio.event
def SyncTonePlayed(sid, data):
    global Browser_Offset
    Browser_Offset = data["browserTimestamp"]



@sio.event
def startRecordingAudio(sid, data):
    # syncClocks()
    clsAudioHandler.startRecordingAudio(data)

@sio.event
def stopRecordingAudio(sid, data):
    # syncClocks()
    clsAudioHandler.stopRecordingAudio(data)
    # print("stopRecordingAudio", time.time()*1000)
    # clsAudioHandler.handleStoppingSensorsRecording(data)
    




@sio.event
def DoneStreamingAudioData(sid, data):
    print("Server time when got that audio ended and the file is uploaded", time.time() * 1000)
    clsAudioHandler.handleStoppingAudioRecording(data)
    
    



    

@flaskApp.route('/uploadAudioPCM', methods=['POST'])
def upload_pcm():
    # ensure output directory exists
    
    full_path = os.path.join(typingSessionsPath, audioOutputFile)
    clsAudioHandler.SessionID =  clsAudioHandler.saveStoppedAudioRecording()

    try:
        # open in append-binary mode
        with open(full_path, 'ab') as f:
            # request.stream is a file-like wrapper over the WSGI input
            chunk_size = 4096
            while True:
                chunk = request.stream.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        app.logger.error(f"Failed writing PCM chunk: {e}")
        abort(500)
    
    return ('', 204)



@flaskApp.route("/api/KeystrokeSensorStream", methods=["POST"])
def KeystrokeSensorStream():
    global typingSessionsPath, keyStrokeSensorOutputFile

    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400

        uploaded_file = request.files["file"]

        if uploaded_file.filename == "":
            return jsonify({"status": "error", "message": "Empty filename"}), 400

        full_path = os.path.join(typingSessionsPath, keyStrokeSensorOutputFile)

        # Save the raw file content (only CSV data, no headers)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        uploaded_file.save(full_path)

        clsAudioHandler.handleStoppingSensorsRecording()

        return jsonify({"status": "success", "message": f"File saved as {keyStrokeSensorOutputFile}"}), 200

    except Exception as e:
        print(f"Error handling file upload: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500




@sio.event
def startRecordingSensorsForScrolling(sid, data):
    global ScrollMovementStarted, ScrollingSessionStartTimestamp, watchSID
    if isNotValidWatchConnection() or SensorRecordingStarted:
        return
    #start recording sensors on the watch
    # if not ScrollMovementStarted:
    # sio.emit("StopRecordingSensors", to=watchSID)
    sio.emit("StartRecordingSensors", "api/sensorStream")
    print("got startRecordingSensors")
    ScrollingSessionStartTimestamp = data['startScrollingTimestamp']
    ScrollMovementStarted = True

@sio.event
def stopRecordingSensorsForScrolling(sid, data):
    global ScrollMovementStarted, SensorOutputFile, scrollingDataPath, ScrollingSessionStartTimestamp, ScrollingSessionEndTimestamp, watchSID
    
    if isNotValidWatchConnection() or SensorRecordingStarted:
        return
    #stop and process the data coming from the watch
    # if ScrollMovementStarted:
    print("got stop recording scrolling data")
    sio.emit("StopRecordingSensors")
    ScrollingSessionEndTimestamp = data['endScrollingTimestamp']
    

    
    
    
        
@flaskApp.route("/api/sensorStream", methods=["POST"])
def scorlling_sensor_stream():
    global ScrollMovementStarted, scrollingDataPath, SensorOutputFile, ScrollingSessionEndTimestamp

    if not ScrollMovementStarted:
        return jsonify({"status": "ignored", "message": "Scroll movement not active"}), 200

    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400

        uploaded_file = request.files["file"]
        if uploaded_file.filename == "":
            return jsonify({"status": "error", "message": "Empty filename"}), 400

        full_path = os.path.join(scrollingDataPath, SensorOutputFile)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        uploaded_file.save(full_path)

        with dbapp.app_context():
            # Query KeyPress records within the time range
            Scrolls = Scrolling.query.filter(
                Scrolling.StartTimestamp >= ScrollingSessionStartTimestamp,
                Scrolling.EndTimestamp <= ScrollingSessionEndTimestamp
            ).all()

            

            # Check if there are any key presses in the time range
            if not Scrolls:
                print("No scrolls found within the specified time range.", ScrollingSessionStartTimestamp, ScrollingSessionEndTimestamp)
                return jsonify({"status": "success", "message": "Data written"}), 200
            # Get the earliest KeyDownTimestamp (start of the session)
            start_scroll = min(Scrolls, key=lambda x: x.StartTimestamp)

            # Get the latest KeyUpTimestamp (end of the session)
            end_scroll = max(Scrolls, key=lambda x: x.EndTimestamp)

            # Extract the timestamps and KeyIDs
            start_timestamp = ScrollingSessionStartTimestamp
            end_timestamp = ScrollingSessionEndTimestamp
            watch_Offset = 0
            
            
            start_scroll_id = start_scroll.ID  # Get the StartscrollID
            end_scroll_id = end_scroll.ID  # Get the EndscrollID

            # Create a new Sessions object
            new_session = ActivitySessions(
                StartTimestamp=start_timestamp,
                EndTimestamp=end_timestamp,
                DataFileName=scrollingDataPath+SensorOutputFile,
                Processed=0,  # Default to 0 (FALSE)
                SessionType=2,  # scrolling session
                userID=UserID,
                StartScrollingID=start_scroll_id,  # Set the StartscrollID
                EndScrollingID=end_scroll_id,  # Set the EndscrollID
                WatchOffset=watch_Offset,
                BrowserOffset=Browser_Offset
            )

            # Add the new session to the database session
            db.session.add(new_session)

            # Commit the transaction
            db.session.commit()

            SessionID = new_session.ID
            print(SessionID)

            if SessionID is not None:
                result = process_scrolling_threaded(str(new_session.ID))
                print(result)
            else:
                print("SessionID is None")

            SensorOutputFile = str(uuid.uuid4()) + '.csv'
            ScrollMovementStarted = False 

        return jsonify({"status": "success", "message": "Data written"}), 200

    except Exception as e:
        print(f"Error handling sensor data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
        
# @sio.event
# def SensorStream(sid, data):
#     global ScrollMovementStarted, scrollingDataPath, SensorOutputFile
#     if ScrollMovementStarted:
#         try:
#             #print(data)
#             #print(f"First 10 bytes of audio data: {audio_data[:10]}")
#             # Append the audio data to the file
#             with open(scrollingDataPath+SensorOutputFile, "a") as f:
#                 f.write(data + '\n')

#             #print(f"Received audio buffer of size: {len(audio_data)} bytes")
#         except Exception as e:
#             print(f"Error handling audio buffer: {e}")



@sio.event
def startRecordingSensorsForMouseMovement(sid, data):
    global MouseMovementStarted, MouseMovementSessionStartTimestamp, watchSID
    #start recording sensors on the watch
    if not MouseMovementStarted and not isNotValidWatchConnection():
        MouseMovementSessionStartTimestamp = data['startMouseMovementTimestamp']
        print("got start recording linear acceleration")
        sio.emit("StartRecordingLinearAcceleration")
        MouseMovementStarted = True

@sio.event
def stopRecordingSensorsForMouseMovement(sid, data):
    global MouseMovementID, MouseMovementStarted, MouseMovementSessionEndTimestamp, MouseMovementSessionStartTimestamp, MouseOutputFile, watchSID
    #stop and process the data coming from the watch
    if MouseMovementStarted and not isNotValidWatchConnection():
        print("got stop recording mouse data")
        sio.emit("StopRecordingLinearAcceleration")
        MouseMovementSessionEndTimestamp = data['MouseMovementEndTimestamp']
        with dbapp.app_context():
            # Query MouseMovement records within the time range
            MouseMovements = MouseMovement.query.filter(
                MouseMovement.StartTimestamp >= MouseMovementSessionStartTimestamp,
                MouseMovement.EndTimestamp <= MouseMovementSessionEndTimestamp
            ).all()

            

            # Check if there are any key presses in the time range
            if not MouseMovements:
                print("No mouse movements found within the specified time range.", ScrollingSessionStartTimestamp, ScrollingSessionEndTimestamp)
                return
            # Get the earliest KeyDownTimestamp (start of the session)
            start_Movement = min(MouseMovements, key=lambda x: x.StartTimestamp)

            # Get the latest KeyUpTimestamp (end of the session)
            end_Movement = max(MouseMovements, key=lambda x: x.EndTimestamp)

            # Extract the timestamps and KeyIDs
            start_timestamp = MouseMovementSessionStartTimestamp
            end_timestamp = MouseMovementSessionEndTimestamp
            watch_Offset = 0
            
            
            start_mouse_id = start_Movement.ID  # Get the StartMouseID
            end_mouse_id = end_Movement.ID  # Get the EndMouseID

            # Create a new Sessions object
            new_session = ActivitySessions(
                StartTimestamp=start_timestamp,
                EndTimestamp=end_timestamp,
                DataFileName=mouseMovementSessionsPath+MouseOutputFile,
                Processed=0,  # Default to 0 (FALSE)
                SessionType=4,  # scrolling session
                userID=UserID,
                StartMouseMovementID=start_mouse_id,  # Set the StartMouseID
                EndMouseMovementID=end_mouse_id,  # Set the EndMouseID
                WatchOffset=watch_Offset,
                BrowserOffset=Browser_Offset
            )

            # Add the new session to the database session
            db.session.add(new_session)

            # Commit the transaction
            db.session.commit()

            SessionID = new_session.ID
            print(SessionID)

            if SessionID is not None:
                result = process_mouseMovement_threaded(str(new_session.ID))
                print(result)
            else:
                print("SessionID is None")

            MouseOutputFile = str(uuid.uuid4()) + '.csv'



        MouseMovementStarted = False


@sio.event
def LinearAccelStream(sid, data):
    global MouseMovementStarted, mouseMovementSessionsPath, MouseOutputFile
    if MouseMovementStarted:
        try:
            #print(data)
            #print(f"First 10 bytes of audio data: {audio_data[:10]}")
            # Append the audio data to the file
            with open(mouseMovementSessionsPath+MouseOutputFile, "a") as f:
                f.write(data + '\n')

            #print(f"Received audio buffer of size: {len(audio_data)} bytes")
        except Exception as e:
            print(f"Error handling audio buffer: {e}")




@sio.event
def testingDebug(sid, data):
    print("debugging---------------------------------------",data)



class clsActivityRecorder:
    AudioOutputPath, SensorOutputPath = str(uuid.uuid4()) + '.pcm', str(uuid.uuid4()) + '.csv'
    ActivitySessionsPath = "SessionsData/ActivitySessions/"
    ActivityName = ""
    StartTimestamp, StopTimestamp = 0, 0
    ActivityID = -1
    @staticmethod
    def startRecordingActivity(data):
        
        if isNotValidWatchConnection():
            return
        #start recording audio from the watch
        clsActivityRecorder.StartTimestamp = data["StartTimestamp"]
        clsActivityRecorder.ActivityName = data["ActivityName"]
        
        payload  = {"endpoint" : "uploadActivityAudioPCM", "WhenDoneRecording": "DoneStreamingActivityAudioData" }
        
        sio.emit("startRecordingAudio", payload , to=audioServiceSID)
        sio.emit("StopRecordingSensors", to=sensorServiceSID)
        sio.emit("StartRecordingSensors", "/api/AllActivitySensorStream", to=sensorServiceSID)
    
    @staticmethod
    def stopRecordingActivity(data):
        print("got stop recording activity")
        global UserID
        clsActivityRecorder.StopTimestamp = data["StopTimestamp"]
        
        with dbapp.app_context():
            #inserting the activity record into the database
            # Step 1: Check if ActivityType already exists
            activity_type = clsActivityRecorder.get_or_create_activity_type(clsActivityRecorder.ActivityName)

            if not activity_type:
                # Step 2: Create and add new ActivityType
                activity_type = ActivityType(ActivityName=clsActivityRecorder.ActivityName)
                db.session.add(activity_type)
                db.session.commit()  # Commit now to get the new ActivityTypeID

            # Step 3: Create the new Activity with the resolved ActivityTypeID
            new_activity = Activity(
                StartTimestamp=clsActivityRecorder.StartTimestamp,
                EndTimestamp=clsActivityRecorder.StopTimestamp,
                ActivityTypeID=activity_type.ActivityTypeID,  # Use FK
                userID=UserID
            )

            # Step 4: Add and commit the new activity
            db.session.add(new_activity)
            db.session.commit()

            # Step 5: Store the activity ID for later use
            clsActivityRecorder.ActivityID = activity_type.ActivityTypeID

            
        sio.emit("StopRecordingSensors", to=sensorServiceSID)
        sio.emit("stopRecordingAudio" , to=audioServiceSID)
    
    @staticmethod
    def get_or_create_activity_type(name):
        activity_type = ActivityType.query.filter_by(ActivityName=name).first()
        if not activity_type:
            activity_type = ActivityType(ActivityName=name)
            db.session.add(activity_type)
            db.session.commit()  # Commit to assign ID
        return activity_type

    @staticmethod
    def HandleStoppingAllActivitySensorRecording():
        # Create a new Sessions object
        with dbapp.app_context():
            new_session = ActivitySessions(
                StartTimestamp=clsActivityRecorder.StartTimestamp,
                EndTimestamp=clsActivityRecorder.StopTimestamp,
                DataFileName=clsActivityRecorder.ActivitySessionsPath
                +clsActivityRecorder.SensorOutputPath,
                Processed=0,  # Default to 0 (FALSE)
                SessionType=16,  # all activity session
                userID=UserID,
                ActivityID=clsActivityRecorder.ActivityID,
                WatchOffset=0,
                BrowserOffset=0
            )

            # Add the new session to the database session
            db.session.add(new_session)

            # Commit the transaction
            db.session.commit()

            clsActivityRecorder.SensorOutputPath = str(uuid.uuid4()) + '.csv'

    @staticmethod
    def allActivitySensorStream(data):
        try:
            #print(data)
            #print(f"First 10 bytes of audio data: {audio_data[:10]}")
            # Append the audio data to the file
            with open(clsActivityRecorder.ActivitySessionsPath + 
                      clsActivityRecorder.SensorOutputPath, "a") as f:
                f.write(data + '\n')

            #print(f"Received audio buffer of size: {len(audio_data)} bytes")
        except Exception as e:
            print(f"Error handling audio buffer: {e}")

    @staticmethod
    def handleStoppingActivityAudioRecording(data):
        if isNotValidWatchConnection():
            return
        
        SessionID = None

        # Push an application context
        with dbapp.app_context():
            
            

            

            

            # Extract the timestamps and KeyIDs
            start_timestamp = data["startTimestamp"]
            end_timestamp = data["endTimestamp"]
            watch_Offset = int(data["watchOffset"])
            # print(watch_Offset, Browser_Offset)
            
            

            # Create a new Sessions object
            new_session = ActivitySessions(
                StartTimestamp=start_timestamp,
                EndTimestamp=end_timestamp,
                DataFileName=clsActivityRecorder.ActivitySessionsPath
                +clsActivityRecorder.AudioOutputPath,
                Processed=0,  # Default to 0 (FALSE)
                SessionType=16,  # all activity session
                userID=UserID,
                ActivityID=clsActivityRecorder.ActivityID,  
                WatchOffset=watch_Offset,
                BrowserOffset=Browser_Offset
            )

            # Add the new session to the database session
            db.session.add(new_session)

            # Commit the transaction
            db.session.commit()

            SessionID = new_session.ID
            

        audio = AudioSegment(
            data=open(clsActivityRecorder.ActivitySessionsPath+
                      clsActivityRecorder.AudioOutputPath, "rb").read(),
            sample_width=2,  # 16-bit PCM
            frame_rate=44100,
            channels=1
        )

        # Normalize the audio
        # normalized_audio = audio.normalize()

        # Export to WAV
        audio.export(clsActivityRecorder.ActivitySessionsPath+
                      clsActivityRecorder.AudioOutputPath+".wav", format="wav")
        clsActivityRecorder.AudioOutputPath = str(uuid.uuid4()) + '.pcm'

        
        

        if SessionID is not None:
            print("audio sessionID for acitvity is ", SessionID)
        else:
            print("SessionID is None")


class clsAudioHandler:
    StoppedRecording = False
    SessionID = None
    @staticmethod
    def startRecordingAudio(data):
        global TypingSessionStartTimestamp, Browser_Offset, SensorRecordingStarted
        clsAudioHandler.StoppedRecording = False
        if isNotValidWatchConnection():
            return
        #start recording audio from the watch
        TypingSessionStartTimestamp  = data["time"]
        # Browser_Offset = data['BrowserOffset']
        print("got start recording data event", data["time"], " server time: ", time.time() * 1000)

        payload  = {"endpoint" : "uploadAudioPCM", "WhenDoneRecording": "DoneStreamingAudioData" }
        # sio.emit("stopRecordingAudio", to=watchSID)
        sio.emit("startRecordingAudio", payload, to=audioServiceSID)
        sio.emit("StopRecordingSensors", to=sensorServiceSID)
        sio.emit("StartRecordingSensors", "api/KeystrokeSensorStream", to=sensorServiceSID)
        SensorRecordingStarted = True
    
    @staticmethod
    def stopRecordingAudio(data):
        global TypingSessionEndTimestamp, UserID, SensorRecordingStarted
        if isNotValidWatchConnection():
            return
        # clsAudioHandler.StoppedRecording = True
        
        TypingSessionEndTimestamp = data['time']
        UserID = data['UserID']
        print("got stop recording data event", TypingSessionStartTimestamp, TypingSessionEndTimestamp, " server time: ", time.time() * 1000)
        sio.emit("stopRecordingAudio", to=audioServiceSID)
        sio.emit("StopRecordingSensors", to=sensorServiceSID)
        SensorRecordingStarted = False
    
    @staticmethod
    def saveStoppedAudioRecording():
        global audioOutputFile, UserID, Browser_Offset, TypingSessionStartTimestamp, TypingSessionEndTimestamp
        if isNotValidWatchConnection():
            return
        # clsAudioHandler.StoppedRecording = True
        #print(sid)
        #print(data)
        SessionID = None
        # Push an application context
        with dbapp.app_context():
            # Query KeyPress records within the time range
            key_presses = KeyPress.query.filter(
                KeyPress.KeyDownTimestamp >= TypingSessionStartTimestamp,
                KeyPress.KeyUpTimestamp <= TypingSessionEndTimestamp
            ).all()

            # print(key_presses[:10])

            # Check if there are any key presses in the time range
            if not key_presses:
                print("No key presses found within the specified time range.")
                return
            # Get the earliest KeyDownTimestamp (start of the session)
            start_key_press = min(key_presses, key=lambda x: x.KeyID)

            # Get the latest KeyUpTimestamp (end of the session)
            end_key_press = max(key_presses, key=lambda x: x.KeyID)

            # Extract the timestamps and KeyIDs
            start_timestamp = 0
            end_timestamp = 0
            watch_Offset = int(TypingSessionEndTimestamp)
            # print(watch_Offset, Browser_Offset)
            print("end time recording from watch", end_timestamp)
            start_key_id = start_key_press.KeyID  # Get the StartKeyID
            end_key_id = end_key_press.KeyID  # Get the EndKeyID

            # Create a new Sessions object
            new_session = ActivitySessions(
                StartTimestamp=start_timestamp,
                EndTimestamp=end_timestamp,
                DataFileName=typingSessionsPath+audioOutputFile,
                Processed=0,  # Default to 0 (FALSE)
                SessionType=1,  # typing session
                userID=UserID,
                StartKeyID=start_key_id,  # Set the StartKeyID
                EndKeyID=end_key_id,  # Set the EndKeyID
                WatchOffset=watch_Offset,
                BrowserOffset=Browser_Offset
            )

            # Add the new session to the database session
            db.session.add(new_session)

            # Commit the transaction
            db.session.commit()

            SessionID = new_session.ID

            return SessionID
            

        

        

    @staticmethod
    def handleStoppingAudioRecording(data):
        global audioOutputFile, typingSessionsPath
        start_timestamp = data["startTimestamp"]
        end_timestamp = data["endTimestamp"]

        print("Processing the Audio Data")

        # Load the raw PCM audio
        try:
            with open(typingSessionsPath + audioOutputFile, "rb") as f:
                audio = AudioSegment(
                    data=f.read(),
                    sample_width=2,  # 16-bit PCM
                    frame_rate=44100,
                    channels=1
                )
        except FileNotFoundError:
            print(f"Error: Audio file not found at {typingSessionsPath + audioOutputFile}")
            return
        except Exception as e:
            print(f"Error loading audio file: {e}")
            return

        # Export to WAV
        wav_output_file = typingSessionsPath + audioOutputFile + ".wav"
        try:
            audio.export(wav_output_file, format="wav")
            print(f"Audio exported to {wav_output_file}")
        except Exception as e:
            print(f"Error exporting audio to WAV: {e}")
            return

        # --- Update timestamps in the database ---
        if clsAudioHandler.SessionID is not None:
            with dbapp.app_context():
                session_to_update = ActivitySessions.query.get(clsAudioHandler.SessionID)
                if session_to_update:
                    session_to_update.StartTimestamp = start_timestamp
                    session_to_update.EndTimestamp = end_timestamp
                    try:
                        db.session.commit()
                        print(f"Session {clsAudioHandler.SessionID} timestamps updated successfully.")
                    except Exception as e:
                        db.session.rollback()
                        print(f"Error updating session timestamps: {e}")
                else:
                    print(f"Session with ID {clsAudioHandler.SessionID} not found for update.")
        else:
            print("clsAudioHandler.SessionID is None, cannot update timestamps.")
        # --- End of update section ---

        # Generate a new filename for the next recording
        audioOutputFile = str(uuid.uuid4()) + '.pcm'

        if clsAudioHandler.SessionID is not None:
            result = process_audio_threaded(str(clsAudioHandler.SessionID))
            print(result)
        else:
            print("SessionID is None, cannot trigger audio processing.")
        
        clsAudioHandler.SessionID = None
    
    @staticmethod 
    def handleStoppingSensorsRecording():
        global keyStrokeSensorOutputFile, UserID, Browser_Offset, TypingSessionStartTimestamp, TypingSessionEndTimestamp
        if isNotValidWatchConnection():
            return

        #print(sid)
        #print(data)
        SessionID = None
        # Push an application context
        with dbapp.app_context():
            # Query KeyPress records within the time range
            key_presses = KeyPress.query.filter(
                KeyPress.KeyDownTimestamp >= TypingSessionStartTimestamp,
                KeyPress.KeyUpTimestamp <= TypingSessionEndTimestamp
            ).all()

            # print(key_presses[:10])

            # Check if there are any key presses in the time range
            if not key_presses:
                print("No key presses found within the specified time range.")
                return
            # Get the earliest KeyDownTimestamp (start of the session)
            start_key_press = min(key_presses, key=lambda x: x.KeyDownTimestamp)

            # Get the latest KeyUpTimestamp (end of the session)
            end_key_press = max(key_presses, key=lambda x: x.KeyUpTimestamp)

            # Extract the timestamps and KeyIDs
            start_timestamp = TypingSessionStartTimestamp
            end_timestamp = TypingSessionEndTimestamp
            watch_Offset = 0
            # print(watch_Offset, Browser_Offset)
            
            start_key_id = start_key_press.KeyID  # Get the StartKeyID
            end_key_id = end_key_press.KeyID  # Get the EndKeyID

            # Create a new Sessions object
            new_session = ActivitySessions(
                StartTimestamp=start_timestamp,
                EndTimestamp=end_timestamp,
                DataFileName=typingSessionsPath+keyStrokeSensorOutputFile,
                Processed=0,  # Default to 0 (FALSE)
                SessionType=8,  # typing sensor session
                userID=UserID,
                StartKeyID=start_key_id,  # Set the StartKeyID
                EndKeyID=end_key_id,  # Set the EndKeyID
                WatchOffset=watch_Offset,
                BrowserOffset=Browser_Offset
            )

            # Add the new session to the database session
            db.session.add(new_session)

            # Commit the transaction
            db.session.commit()

            SessionID = new_session.ID
            keyStrokeSensorOutputFile = str(uuid.uuid4()) + '.csv'

            if SessionID is not None:
                result = process_keystroke_sensors_threaded(str(new_session.ID))
                print(result)
            else:
                print("SessionID is None for process_keystroke_sensors")

    
    
    
    



@sio.event
def messageSent(sid, data):
    clsMessageHandler.onMessageReceived(data)



class clsMessageHandler:
    TypingStartTimestamp = None
    
    @staticmethod
    def onMessageReceived(data):
        if clsMessageHandler.TypingStartTimestamp is None:
            clsMessageHandler.TypingStartTimestamp = TypingSessionStartTimestamp

        
        with dbapp.app_context():
            # Query KeyPress records within the time range
            key_presses = KeyPress.query.filter(
                KeyPress.KeyDownTimestamp >= clsMessageHandler.TypingStartTimestamp,
                KeyPress.KeyUpTimestamp <= data['timestamp']
            ).all()

            # print(key_presses[:10])

            # Check if there are any key presses in the time range
            if not key_presses:
                print("No key presses found within the specified time range.")
                return
            # Get the earliest KeyDownTimestamp (start of the session)
            start_key_press = min(key_presses, key=lambda x: x.KeyDownTimestamp)

            # Get the latest KeyUpTimestamp (end of the session)
            end_key_press = max(key_presses, key=lambda x: x.KeyUpTimestamp)


            start_key_id = start_key_press.KeyID  # Get the StartKeyID
            end_key_id = end_key_press.KeyID  # Get the EndKeyID

            new_message = Message(
                SentTimestamp = data['timestamp'],
                MessageContent = data['message'],
                userID = data["UserID"],
                StartKeyID = start_key_id,
                EndKeyID = end_key_id
            )

            db.session.add(new_message)

            # Commit the transaction
            db.session.commit()
            clsMessageHandler.TypingStartTimestamp = int(data['timestamp'])
            '''
            so basically here, I take the time the message started typing and the time it was sent to
            extract the keystrokes of that message, then the new starttime will be the endtimestamp of
            the old message
            '''




# Wrap the Socket.IO server with a WSGI application
# Mount both under one WSGI app:
app = socketio.WSGIApp(sio, flaskApp)



# Start the server
if __name__ == "__main__":
    print("Socket.IO server started on http://0.0.0.0:5001")
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 5001)), app, log_output=False)
    