

var socketio = io();

const messages = document.getElementById("messages");

const createMessage = (name, msg) => {
    const content = `
    <div class="text">
        <span>
            <strong>${name}</strong>: ${msg}
        </span>
        <span class="muted">
            ${new Date().toLocaleString()}
        </span>
    </div>
    `;
    messages.innerHTML += content;
};
function getCurrentTime(){

    return  Date.now();
}

let userID = 0;
socketio.on("message", (data) => {
    createMessage(data.name, data.message);
});

//ajax to handle the questionnaire submission without leaving the page
const form = document.getElementById('surveyForm');

  form.addEventListener('submit', function(e) {
    e.preventDefault();                // stop the normal page navigation
    const formData = new FormData(this);
    formData.set('userID', userID);

    fetch(this.action, {
      method: 'POST',
      body: formData
    })
    .then(res => {
      if (!res.ok) throw new Error(res.statusText);
      // Clear the form now that it's been accepted
    //   form.reset();
      console.log('Server got form.');  // client-side confirmation
    })
    .catch(console.error);
  });

socketio.on("SetUserID", (data) => {
    userID = data.userID
    console.log("user ID", userID)
})

socketio.on("getBrowserTime", (data) => {
    console.log("got getBrowserTime")
    try {
        socketio.emit("BrowserTime", {time: getCurrentTime()})
    } catch (error) {
        console.error('Error inside getBrowserTime listener:', error);
    }
    
})

socketio.on("disconnect", (reason) => {
    console.log('Socket disconnected. Reason:', reason);
})


const sendMessage = () => {
    const message = document.getElementById("message");
    if (message.value == "") return;
    socketio.emit("message", { data: message.value , timestamp: getCurrentTime(), UserID: userID});
    message.value = "";
};

const sendActivityMessage = () => {
    const message = document.getElementById("activityMessage");
    if (message.value == "") return;
    socketio.emit("activityMessage", { data: message.value , StartTimestamp: getCurrentTime()});
    message.value = "";
    
}

const sendStopActivityMessage = () => {
    socketio.emit("StopRecordingActivity", {StopTimestamp: getCurrentTime()});
}






//handling keyboard events

var timePressed = new Map();
let isNotTyping = true;
let browserOffset = 0;
let finishedTyping;





// //function to signal when the user starts typing
function sendStartTyping(){
    if(isNotTyping){
        
        // synchronizeWithServer().then((offset) => {
        //     if (offset !== null) {
        //         browserOffset = offset;
        //     } else {
        //         console.log("Synchronization failed.");
        //     }
        // });
        // console.log("browser offset", browserOffset)
        
        socketio.emit("TypingStarted", {browserTimeOffset: browserOffset, SessionStartTimestamp: getCurrentTime()})
        isNotTyping = false;

    }
}





// Global AudioContext instance
let audioCtx;
// Reference points to synchronize AudioContext time with Unix time
let audioContextReferenceUnixTime = null; // Unix timestamp (ms) when audioCtx.currentTime was recorded
let audioContextReferenceAudioTime = null; // audioCtx.currentTime (s) at the reference point

/**
 * Plays a synchronized sine wave tone and returns the Unix timestamp (milliseconds)
 * of when the tone is scheduled to start within the AudioContext.
 */
async function playSyncTone(frequency = 2000, duration = 200) {
    // Lazily create AudioContext on first user interaction or first call to this function
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        // Attempt to resume audio context if it's suspended (common on mobile)
        if (audioCtx.state === 'suspended') {
            try {
                await audioCtx.resume();
                console.log("AudioContext resumed.");
            } catch (e) {
                console.error("Failed to resume AudioContext:", e);
                return null;
            }
        }
        // Establish the reference point as soon as the AudioContext is active
        audioContextReferenceUnixTime = Date.now();       // Current Unix time in milliseconds
        audioContextReferenceAudioTime = audioCtx.currentTime; // Current audio context time in seconds
        console.log(`AudioContext created and references set. Reference Unix: ${audioContextReferenceUnixTime}, AudioTime: ${audioContextReferenceAudioTime}`);
    }

    // Check if reference times are properly set after potential initialization
    if (audioContextReferenceUnixTime === null || audioContextReferenceAudioTime === null) {
        console.error("AudioContext reference times are not set. Cannot play tone.");
        return null;
    }

    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();

    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(frequency, audioCtx.currentTime);

    // Set initial volume to 1 and then ramp down to a very low value (near silent)
    // This creates a fade-out effect and prevents clicks at the end of the tone.
    gainNode.gain.setValueAtTime(1, audioCtx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration / 1000);

    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);

    // This is the precise time in the audio context's timeline when the tone will *actually* start
    const toneScheduledAudioTime = audioCtx.currentTime;
    const time = getCurrentTime()
    oscillator.start(toneScheduledAudioTime); // Schedule start at current audio context time
    oscillator.stop(toneScheduledAudioTime + duration / 1000); // Schedule stop after duration

    // Disconnect nodes after the tone has played to free up resources
    oscillator.onended = () => {
        oscillator.disconnect();
        gainNode.disconnect();
    };

    // Calculate the corresponding Unix timestamp (in milliseconds)
    // Unix Time = (Reference Unix Time) + (Time elapsed in AudioContext since reference) * 1000
    const unixStartTimeMillis = audioContextReferenceUnixTime +
                                (toneScheduledAudioTime - audioContextReferenceAudioTime) * 1000;

    return time;
}


const logKeyDown = async (event) => {
    const now = getCurrentTime();

    timePressed.set(event.key, now);
    sendStartTyping();
};

const sendFinishedTyping = async () => {
    await socketio.emit("TypingStopped", { SessionEndTimestamp: getCurrentTime(), userID: userID });
    isNotTyping = true;
};



const logKeyUp = async (event) => {
    const key = event.key;
    const releaseTime = getCurrentTime();
    socketio.emit("keyPressed", { KeyDownTimestamp: timePressed.get(key), KeyUpTimestamp: releaseTime, userID: userID, KeyPressed: key });
    clearTimeout(finishedTyping);
    finishedTyping = setTimeout(async () => {
        // socketio.emit("BrowserTime", {time: getCurrentTime()})
        // Play tone while watch is still recording
        const syncTime = await playSyncTone(18000, 200);
        // socketio.emit("BrowserTime", {time: getCurrentTime()})
        socketio.emit("SyncTonePlayed", { browserTimestamp: syncTime });
        if (syncTime !== null) {
            // Assuming `socketio` is defined globally or imported
            // socketio.emit("SyncTonePlayed", { browserTimestamp: syncTime });
            console.log(`Sync Tone played at Unix Timestamp: ${syncTime} ms`);
        } else {
            console.error("Failed to get sync tone timestamp.");
        }

        

       
        

        // Slight delay before telling the watch to stop, to ensure tone is fully recorded
        setTimeout(sendFinishedTyping, 500); // allow tone (e.g., 200ms) to finish

    }, 30000);
};

document.addEventListener("keydown", async (event) => logKeyDown(event));
document.addEventListener("keyup", async (event) => logKeyUp(event));





//handling scrolling


let lastScrollPosition = window.scrollY;
let isScrolling;
let startTimestamp;
let lastDirection = null; // Track the last scroll direction
let stoppedScrolling = true;

const enScrollingDirection = {
    "Down": 1,
    "Up": 2
};

function sendScrollEvent(startTimestamp, endTimestamp, scrollingDirection) {
    socketio.emit('Scrolling', {
        "startTimestamp": startTimestamp,
        "endTimestamp": endTimestamp,
        "scrollingDirection": lastDirection,
        "userID": userID
    });
}

function sendScrollEnded(startTimestamp, endTimestamp, scrollingDirection) {
    sendScrollEvent(startTimestamp, endTimestamp - 1000, lastDirection);

    socketio.emit('ScrollingEnded', {
        "endTimestamp": endTimestamp,
    });
}

function handleWindowScroll(){
    const currentScrollPosition = window.scrollY;
    handleScroll(currentScrollPosition);
}

function handleMessageScroll(){
    const currentScrollPosition = messages.scrollTop;
    handleScroll(currentScrollPosition);
}

function sendScrollStarted(){
    if(stoppedScrolling){
        socketio.emit('ScrollingStart', {'StartTimestamp': getCurrentTime()});
        stoppedScrolling = false;
    }
}

// Function to handle scroll events
function handleScroll(currentScrollPosition) {
    sendScrollStarted();

    // Determine scroll direction
    let scrollingDirection;
    if (currentScrollPosition > lastScrollPosition) {
        scrollingDirection = enScrollingDirection["Down"];
    } else {
        scrollingDirection = enScrollingDirection["Up"];
    }

    // If the direction has changed, send the previous scroll event
    if (scrollingDirection !== lastDirection && lastDirection !== null) {
        const endTimestamp = getCurrentTime();

        // Send the scroll event for the previous direction
        sendScrollEvent(startTimestamp, endTimestamp, lastDirection);

        // Reset the start timestamp for the new direction
        startTimestamp = getCurrentTime();
        
    }

    // If scrolling just started, record the start timestamp
    if (!startTimestamp) {
        startTimestamp = getCurrentTime();
    }

    // Clear the previous timeout (if any)
    clearTimeout(isScrolling);

    // Set a timeout to detect when scrolling stops
    isScrolling = setTimeout(() => {
        const endTimestamp = getCurrentTime();

        // Send the scroll event for the current direction
        sendScrollEnded(startTimestamp, endTimestamp, scrollingDirection);

        // Reset the start timestamp and last direction
        startTimestamp = null;
        lastDirection = null;
        stoppedScrolling = true;
    }, 1000); // Adjust the delay as needed

    // Update the last scroll position and direction
    lastScrollPosition = currentScrollPosition;
    lastDirection = scrollingDirection;
}

 

// Attach the scroll event listener to the window
window.addEventListener("scroll", handleWindowScroll);
messages.addEventListener("scroll", handleMessageScroll);








//handle mouse movements

let prevX = 0;
let prevY = 0;
let mouseDirection = 0;
let startTime = 0;
let MouseMovementStarted = false;
let enMouseMovement = {
    'Right': 1,
    'Up': 2,
    'Left': 4,
    'Down': 8
};
let timeoutId = null;
const stopDelay = 1000; // 500ms inactivity threshold

// New stop handler function
function handleMouseStop() {
  if (startTime !== 0) {
    const endTime = getCurrentTime();
    sendMouseMovement(mouseDirection, endTime - stopDelay);
    socketio.emit("MouseMovementStopped", {'EndTimestamp': endTime - stopDelay});
    startTime = 0;
    mouseDirection = 0;
    MouseMovementStarted = false
  }
}

//start of mouse movement

function sendMouseMovement(direction, endTime){
    socketio.emit("MouseMovement", {
        "Direction": direction,
        "startTimestamp": startTime,
        "endTimestamp": endTime,
        "userID": userID
    })
    startTime = 0;
}

function sendMouseMovementStarted(){
    startTime = getCurrentTime();
    if(!MouseMovementStarted){
        socketio.emit("MouseMovementStarted", {"startTimestamp": startTime})
        MouseMovementStarted = true;
    }
}

function handleMouseMovement(event){
    if(startTime === 0){
        sendMouseMovementStarted();
        
    }
    
    const currentX = event.clientX;
    const currentY = event.clientY;
  
    // Calculate the direction
    let currentMouseDirection = 0;
    if (currentX > prevX) {
      currentMouseDirection += enMouseMovement['Right'];
    } else if (currentX < prevX) {
      currentMouseDirection += enMouseMovement['Left'];
    }
  
    if (currentY > prevY) {
      currentMouseDirection += enMouseMovement['Down'];
    } else if (currentY < prevY) {
      currentMouseDirection += enMouseMovement['Up'];
    }
    // // Invert Y-axis to match accelerometer convention
    // if (currentY < prevY) {  // Mouse moved up (Y decreased)
    // currentMouseDirection += enMouseMovement['Up'];
    // } else if (currentY > prevY) {  // Mouse moved down (Y increased)
    // currentMouseDirection += enMouseMovement['Down'];
    // }

    if(mouseDirection === 0){
        mouseDirection = currentMouseDirection;
        
    }

    if(mouseDirection !== currentMouseDirection){
        //change in direction
        let endDate = getCurrentTime();

        sendMouseMovement(mouseDirection, endDate);
        mouseDirection = currentMouseDirection;
    }

    prevX = currentX;
    prevY = currentY;

    // Clear any pending stop detection
    clearTimeout(timeoutId);

    timeoutId = setTimeout(handleMouseStop, stopDelay);

}




window.addEventListener('beforeunload', handleMouseStop);
window.addEventListener('unload', handleMouseStop);

// Add these to your existing event listeners
document.addEventListener("visibilitychange", handleVisibilityChange);
window.addEventListener("blur", handleMouseStop);

function handleVisibilityChange() {
  if (document.hidden) {
    handleMouseStop();
  }
}






document.addEventListener("mousemove", (event) => {
    if (stoppedScrolling){
        handleMouseMovement(event)
    }
});