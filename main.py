from webUtils import *
from models import *
from collections import defaultdict


active_connections = defaultdict(set) # key: UserID, Value: set of socket IDs
name = ""




event_queue = queue.Queue() # Our thread-safe queue

# --- Background Task to Process Queue (in Flask-SocketIO's context) ---
# Background worker
def queue_processor_task():
    while True:
        try:
            event_type = event_queue.get(timeout=1)
            
            if event_type == "getBrowserTime_event":
                print(f"Processing event: {event_type}")
                socketioConnection.emit("getBrowserTime")
            event_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Queue processor error: {e}")


@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        DBInteractions.AddUserToDatabase(name)
        return redirect(url_for("room"))

    return render_template("home.html")

def str2bool(val):
    """
    Convert a 'Yes'/'No'/None string into a boolean or None.
    """
    if val == 'Yes':
        return True
    if val == 'No':
        return False
    return None


@app.route('/questionnaire', methods=['POST'])
def questionnaire():
    form = request.form
    
    # === Single-value fields (normalize to stripped string or None) ===
    age                      = (form.get('age') or '').strip() or None
    gender                   = (form.get('gender') or '').strip() or None
    field_of_study           = (form.get('field_of_study') or '').strip() or None
    occupation               = (form.get('occupation') or '').strip() or None
    hours_per_week           = (form.get('hours_per_week') or '').strip() or None
    primary_language         = (form.get('primary_language') or '').strip() or None
    shop_online_freq         = (form.get('shop_online_frequency') or '').strip() or None
    online_banking           = (form.get('online_banking_frequency') or '').strip() or None
    ebay_usage               = (form.get('ebay_usage') or '').strip() or None
    amazon_usage             = (form.get('amazon_usage') or '').strip() or None
    paypal_usage             = (form.get('paypal_usage') or '').strip() or None
    bank_usage               = (form.get('bank_usage') or '').strip() or None

    ever_installed_os        = str2bool((form.get('ever_installed_os') or '').strip())
    ever_designed_website    = str2bool((form.get('ever_designed_website') or '').strip())
    ever_registered_domain   = str2bool((form.get('ever_registered_domain') or '').strip())
    ever_used_telnet_ssh     = str2bool((form.get('ever_used_telnet_ssh') or '').strip())
    ever_changed_firewall    = str2bool((form.get('ever_changed_firewall') or '').strip())

    user_id                  = (form.get('userID') or '').strip() or None

    primary_browser          = (form.get('primary_browser') or '').strip() or None
    primary_browser_version  = (form.get('primary_browser_version') or '').strip() or None

    secondary_browser        = (form.get('secondary_browser') or '').strip() or None
    secondary_browser_version= (form.get('secondary_browser_version') or '').strip() or None

    # === Multi-value fields (checkbox/radio with list support) ===
    education_choices = form.getlist('education') or []
    os_choices        = form.getlist('os')        or []

    raw_os_versions   = form.getlist('os_version')
    os_versions       = [v.strip() for v in raw_os_versions if v.strip()]

    # === Type conversions ===
    if age is not None:
        age = int(age)
    if hours_per_week is not None:
        hours_per_week = int(hours_per_week)
    if user_id is not None:
        user_id = int(user_id)
    print(user_id)
    # === Insert Response ===
    response = Response(
        userID=user_id,
        age=age,
        gender=gender,
        field_of_study=field_of_study,
        occupation=occupation,
        hours_per_week=hours_per_week,
        primary_language=primary_language,
        shop_online_frequency=shop_online_freq,
        online_banking_frequency=online_banking,
        ebay_usage=ebay_usage,
        amazon_usage=amazon_usage,
        paypal_usage=paypal_usage,
        bank_usage=bank_usage,
        ever_installed_os=ever_installed_os,
        ever_designed_website=ever_designed_website,
        ever_registered_domain=ever_registered_domain,
        ever_used_telnet_ssh=ever_used_telnet_ssh,
        ever_changed_firewall=ever_changed_firewall,
        primary_browser=primary_browser,
        primary_browser_version=primary_browser_version,
        secondary_browser=secondary_browser,
        secondary_browser_version=secondary_browser_version
    )
    db.session.add(response)
    db.session.flush()  # assign response.response_id

    # === Insert Education choices ===
    for edu in education_choices:
        db.session.add(ResponseEducation(
            response_id=response.response_id,
            education=edu
        ))

    # === Insert OS entries ===
    version_iter = iter(os_versions)

    for os_name in os_choices:
        if os_name == 'MacOS':
            os_ver = None
        else:
            # pull the next available version, or None if we’ve run out
            os_ver = next(version_iter, None)

        db.session.add(ResponseOS(
            response_id   = response.response_id,
            os_name       = os_name,
            os_version    = os_ver
        ))

    # === Commit all changes ===
    db.session.commit()

    # Return empty 204 (no content)
    return '', 204


@app.route('/sync', methods=['GET'])
def sync():
    # Return the current server time in milliseconds
    server_time = int(time.time() * 1000)
    return jsonify({"timestamp": server_time})

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    userID = DBInteractions.GetUserID(session.get("name"))
    socketioConnection.emit("setUserID", {userID: userID})

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketioConnection.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    for q in quotes_list:
        send(q, to=room)
    send(content, to=room)
    rooms[room]["messages"].append(content)
    sio.emit("messageSent", {"message": data["data"], "timestamp": data["timestamp"], "UserID": data["UserID"]})
    print(f"{session.get('name')} said: {data['data']}")



@socketioConnection.on("activityMessage")
def activityMessage(data):
    #record all the data from the watch
    sio.emit("RecordAllActivities", {"ActivityName": data["data"], "StartTimestamp": data["StartTimestamp"]})
    
@socketioConnection.on("StopRecordingActivity")
def StopRecordingActivity(data):
    print("got stop recording activity")
    sio.emit("StopRecordingActivity", {"StopTimestamp": data["StopTimestamp"]})    

browsersid = None
@socketioConnection.on("connect")
def connect(auth):
    global browsersid, userID, name
    room = session.get("room")
    name = session.get("name")
    active_connections[name].add(request.sid) #request.sid = unique socket ID
    print(f"User {name} connections: {len(active_connections[name])}, {active_connections[name]}")
    # Validate room and name
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    # Join the room
    join_room(room)
    
    # Notify the room that a new user has joined
    send({"name": name, "message": "has entered the room"}, to=room)

    # Get the user's ID
    userID = DBInteractions.GetUserID(name)
    browsersid = request.sid
    print("browser sid: ", browsersid)
    # Send the user's ID to the specific user connection
    socketioConnection.emit("SetUserID", {"userID": userID}, room=request.sid)

    # Update room members count
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketioConnection.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    active_connections[name].discard(request.sid)
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")




@socketioConnection.on("keyPressed")
def keyPressed(data):
    if 'KeyDownTimestamp' not in data:
        return
    NewKeyPress = KeyPress(KeyDownTimestamp = data['KeyDownTimestamp'], 
                           KeyUpTimestamp = data['KeyUpTimestamp'], 
                           userID = data['userID'], 
                           KeyPressed = data['KeyPressed'])
    db.session.add(NewKeyPress)
    db.session.commit()
    
    # print("added", NewKeyPress)

@socketioConnection.on('TypingStarted')
def typingStarted(data):
    #start recording on the watch
    sio.emit("startRecordingAudio" , {"time": data['SessionStartTimestamp'], "BrowserOffset": data['browserTimeOffset']})
    print("typing started")

def sendGetBrowserTime():
    socketioConnection.emit("getBrowserTime", room=browsersid, namespace="/")

@sio.event
def getBrowserTime():
    print("got  get browser time")
    print("browser sid", browsersid)
    event_queue.put("getBrowserTime_event") # You can put more complex data here if needed
    print("Placed 'getBrowserTime_event' in queue.")
    
@socketioConnection.on("SyncTonePlayed")
def SyncTonePlayed(data):
    sio.emit("SyncTonePlayed", {"browserTimestamp": data["browserTimestamp"]})
    




@socketioConnection.on("BrowserTime")
def BrowserTime(data):
    print("got browser time")
    print("browser sid", browsersid)

    sio.emit("BrowserTime", {"time": data["time"]})

@socketioConnection.on("TypingStopped")
def typingStopped(data):
    #stop recording on the watch
    sio.emit("stopRecordingAudio", {"time": data["SessionEndTimestamp"], "UserID": data["userID"]})
    print("typing stopped")

@socketioConnection.on("Scrolling")
def ScrollingEvent(data):
    try:
        NewScroll = Scrolling(
            StartTimestamp = data["startTimestamp"],
            EndTimestamp = data["endTimestamp"],
            Direction = data["scrollingDirection"],
            userID = data["userID"]
        )
        
        db.session.add(NewScroll)
        
        db.session.commit()
    
    
        
        print("added ", NewScroll)
        
    except Exception as e:
        print("printing scroll, ", e)
    #scrolling stopped here so should also integrate with the watch
   
@socketioConnection.on("ScrollingStart")
def ScrollingStarted(data):
    #use this to start the recording on the watch
    print("scrolling started ")
    sio.emit("startRecordingSensorsForScrolling", {"startScrollingTimestamp": data['StartTimestamp']})

@socketioConnection.on("ScrollingEnded")
def ScrollingStarted(data):
    #use this to start the recording on the watch
    print("scrolling ended ")
    sio.emit("stopRecordingSensorsForScrolling", {"endScrollingTimestamp": data["endTimestamp"]})




@socketioConnection.on("MouseMovement")
def mouseMovement(data):
    
    newMouseMovement = MouseMovement(
        StartTimestamp = data['startTimestamp'],
        EndTimestamp = data['endTimestamp'],
        Direction = data["Direction"],
        userID = data["userID"]
    )
    # print(newMouseMovement)
    # sio.emit("stopRecordingSensorsForMouseMovement", {'mouseMovementID': newMouseMovement.ID})
    db.session.add(newMouseMovement)
    db.session.commit()

    #stop recording on the watch


@socketioConnection.on("MouseMovementStarted")
def MouseMovementStarted(data):
    print("mouse movement started")
    sio.emit("startRecordingSensorsForMouseMovement", {"startMouseMovementTimestamp": data['startTimestamp']})
    #start recording on the watch

@socketioConnection.on("MouseMovementStopped")
def MouseMovementStopped(data):
    print("mouse movement stopped")
    sio.emit("stopRecordingSensorsForMouseMovement", {'MouseMovementEndTimestamp': data['EndTimestamp']})

@socketioConnection.on("testingTime")
def testingTime(data):
    print(data, time.time_ns()/1000000)



if __name__ == "__main__":
    socketioConnection.start_background_task(target=queue_processor_task)

    socketioConnection.run(app,host="0.0.0.0",port=5002, debug=True)
    