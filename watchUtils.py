from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, abort, jsonify
import os, uuid, threading
from dotenv import load_dotenv

dbapp = Flask(__name__)
dbapp.config["SECRET_KEY"] = "hjhjsdahhds"

load_dotenv()
# --- PostgreSQL Database Connection Details ---
# Retrieve from environment variables, with fallbacks
DB_NAME = os.getenv('POSTGRES_DB', 'mydatabase')
DB_USER = os.getenv('POSTGRES_USER', 'myuser')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'mypassword')
# IMPORTANT:
# - If your Flask app runs ON THE SAME MACHINE as Docker Desktop (your Mac), use 'localhost'.
# - If your Flask app runs INSIDE ANOTHER DOCKER CONTAINER in the same docker-compose network, use 'db' (the service name).
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# Construct the PostgreSQL SQLAlchemy URI
dbapp.config['SQLALCHEMY_DATABASE_URI'] = \
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

dbapp.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(dbapp)

websiteSID = watchSID = audioServiceSID = sensorServiceSID = 0
audioOutputFile, SensorOutputFile, MouseOutputFile, keyStrokeSensorOutputFile = str(uuid.uuid4()) + '.pcm', str(uuid.uuid4()) + '.csv', str(uuid.uuid4()) + '.csv', str(uuid.uuid4()) + '.csv'

typingSessionsPath, scrollingDataPath, mouseMovementSessionsPath = "SessionsData/TypingSessions/","SessionsData/ScrollingSessions/", "SessionsData/MouseMovementSessions/"
mouseMovementDataPath, scrollingDataPacket, typingDataPath = 'SessionsData/MouseMovementData/', 'SessionsData/ScrollingData', 'SessionsData/KeystrokeData'
# Check and create directories if they don't exist
for path in [typingSessionsPath, scrollingDataPath, mouseMovementSessionsPath, mouseMovementDataPath, scrollingDataPacket, typingDataPath, 'SessionsData/ActivitySessions/']:
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    

TypingSessionStartTimestamp: int = 0
TypingSessionEndTimestamp: int = 0
ScrollingSessionStartTimestamp:int = 0 
ScrollingSessionEndTimestamp: int = 0
MouseMovementSessionStartTimestamp: int = 0
MouseMovementSessionEndTimestamp: int = 0
Browser_Offset = 0
UserID, ScrollID, MouseMovementID = None, None, None

MouseMovementStarted : bool   = False
ScrollMovementStarted: bool =  False
SensorRecordingStarted: bool = False


# --- SQLAlchemy Models for PostgreSQL ---

# --- SQLAlchemy Models for PostgreSQL ---

# --- User Model ---
class User(db.Model):
    __tablename__ = 'users' # 'users' is lowercase in DB, so no quotes needed here
    # PostgreSQL SERIAL maps to db.Integer with primary_key=True
    userID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False) # TEXT in PostgreSQL

    def __repr__(self):
        return f"<User(userID={self.userID}, name='{self.name}')>"

# --- KeyPress Model ---
class KeyPress(db.Model):
    __tablename__ = 'KeyPresses' # This is case-preserved in DB ("KeyPresses")
    KeyID = db.Column(db.Integer, primary_key=True)
    # Use BigInteger for timestamps if they are Unix epoch milliseconds
    KeyDownTimestamp = db.Column(db.BigInteger, nullable=False)
    KeyPressed = db.Column(db.String, nullable=False)
    KeyUpTimestamp = db.Column(db.BigInteger, nullable=False)
    AudioFileName = db.Column(db.String(500), nullable=True)
    # Added SensorFileName as it was in your SQL schema
    SensorFileName = db.Column(db.String(500), nullable=True)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True) # Table 'users' (lowercase), column "userID" (quoted)

    user = db.relationship('User', backref='key_presses')

    def __repr__(self):
        return (f"<KeyPresses(KeyID={self.KeyID}, KeyDownTimestamp={self.KeyDownTimestamp}, " # Corrected 'keyID' to 'KeyID'
                f"KeyUpTimestamp={self.KeyUpTimestamp}, KeyPressed='{self.KeyPressed}', "
                f"AudioFileName={self.AudioFileName}, SensorFileName={self.SensorFileName}, userID={self.userID})>")

# --- Scrolling Model ---
class Scrolling(db.Model):
    __tablename__ = 'Scrolling' # This is case-preserved in DB ("Scrolling")
    ID = db.Column(db.Integer, primary_key=True) # SERIAL for PG
    StartTimestamp = db.Column(db.BigInteger, nullable=False)
    EndTimestamp = db.Column(db.BigInteger, nullable=False)
    DataFileName = db.Column(db.String(500), nullable=True) # Specify string length or use db.Text
    Direction = db.Column(db.Integer, nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True) # Table 'users' (lowercase), column "userID" (quoted)

    user = db.relationship('User', backref='scrolls')

    def __repr__(self):
        return (f"<Scrolling(ID={self.ID}, StartTimestamp={self.StartTimestamp}, "
                f"EndTimestamp={self.EndTimestamp}, DataFileName={self.DataFileName}, "
                f"Direction={self.Direction}, userID={self.userID})>")

# --- MouseMovement Model ---
class MouseMovement(db.Model):
    __tablename__ = 'MouseMovement' # This is case-preserved in DB ("MouseMovement")
    ID = db.Column(db.Integer, primary_key=True) # SERIAL for PG
    StartTimestamp = db.Column(db.BigInteger, nullable=False)
    EndTimestamp = db.Column(db.BigInteger, nullable=False)
    DataFileName = db.Column(db.String(500), nullable=True) # Specify string length or use db.Text
    Direction = db.Column(db.Integer, nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True) # Table 'users' (lowercase), column "userID" (quoted)

    user = db.relationship('User', backref='mouse_movements')

    def __repr__(self):
        return (f"<MouseMovement(ID={self.ID}, StartTimestamp={self.StartTimestamp}, "
                f"EndTimestamp={self.EndTimestamp}, DataFileName={self.DataFileName}, "
                f"Direction={self.Direction}, userID={self.userID})>")
   
# --- ActivityType Model ---
class ActivityType(db.Model):
    __tablename__ = 'ActivityTypes' # This is case-preserved in DB ("ActivityTypes")
    ActivityTypeID = db.Column(db.Integer, primary_key=True) # SERIAL for PG
    ActivityName = db.Column(db.String, nullable=False, unique=True) # TEXT or VARCHAR(255) for PG, unique constraint

    def __repr__(self):
        return f"<ActivityType(ActivityTypeID={self.ActivityTypeID}, ActivityName='{self.ActivityName}')>"

# --- Activities Model ---
class Activity(db.Model):
    __tablename__ = 'Activities' # This is case-preserved in DB ("Activities")
    ID = db.Column(db.Integer, primary_key=True) # SERIAL for PG
    StartTimestamp = db.Column(db.BigInteger, nullable=False)
    EndTimestamp = db.Column(db.BigInteger, nullable=False)
    
    ActivityTypeID = db.Column(db.Integer, db.ForeignKey('ActivityTypes.ActivityTypeID'), nullable=False) # Table "ActivityTypes" (quoted), column "ActivityTypeID" (quoted)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True) # Table 'users' (lowercase), column "userID" (quoted)

    user = db.relationship('User', backref='activities')
    activity_type = db.relationship('ActivityType', backref='activities')

    def __repr__(self):
        return (
            f"<Activity(ID={self.ID}, StartTimestamp={self.StartTimestamp}, "
            f"EndTimestamp={self.EndTimestamp}, ActivityTypeID={self.ActivityTypeID}, userID={self.userID})>"
        )

# --- Messages Model ---
class Message(db.Model):
    __tablename__ = 'Messages' # This is case-preserved in DB ("Messages")
    MessageID = db.Column(db.Integer, primary_key=True) # SERIAL for PG
    SentTimestamp = db.Column(db.BigInteger, nullable=False)
    MessageContent = db.Column(db.Text, nullable=False) # Use db.Text for potentially long content
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False) # Table 'users' (lowercase), column "userID" (quoted)
    # Ensure foreign keys are correctly linked to the KeyPress table
    StartKeyID = db.Column(db.Integer, db.ForeignKey('KeyPresses.KeyID'), nullable=True) # Table "KeyPresses" (quoted), column "KeyID" (quoted)
    EndKeyID = db.Column(db.Integer, db.ForeignKey('KeyPresses.KeyID'), nullable=True) # Table "KeyPresses" (quoted), column "KeyID" (quoted)
    
    # Relationships to KeyPresses, using foreign_keys to distinguish
    user = db.relationship('User', backref='messages')
    start_key = db.relationship('KeyPress', foreign_keys=[StartKeyID], backref='start_messages')
    end_key = db.relationship('KeyPress', foreign_keys=[EndKeyID], backref='end_messages')

    def __repr__(self):
        return (f"<Message(MessageID={self.MessageID}, SentTimestamp={self.SentTimestamp}, "
                f"MessageContent='{self.MessageContent[:50]}...', userID={self.userID}, "
                f"StartKeyID={self.StartKeyID}, EndKeyID={self.EndKeyID})>")

# --- Response Models ---
# One row per submitted response
class Response(db.Model):
    __tablename__ = 'responses' # 'responses' is lowercase in DB, so no quotes needed here
    response_id = db.Column(db.Integer, primary_key=True) # SERIAL for PG
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False) # Table 'users' (lowercase), column "userID" (quoted)
    age = db.Column(db.Integer)
    gender = db.Column(db.String)
    field_of_study = db.Column(db.String)
    occupation = db.Column(db.String)
    hours_per_week = db.Column(db.Integer)
    primary_language = db.Column(db.String)
    shop_online_frequency = db.Column(db.String)
    online_banking_frequency = db.Column(db.String)
    ebay_usage = db.Column(db.String)
    amazon_usage = db.Column(db.String)
    paypal_usage = db.Column(db.String)
    bank_usage = db.Column(db.String)
    # PostgreSQL BOOLEAN for 0/1
    ever_installed_os = db.Column(db.Boolean)
    ever_designed_website = db.Column(db.Boolean)
    ever_registered_domain = db.Column(db.Boolean)
    ever_used_telnet_ssh = db.Column(db.Boolean)
    ever_changed_firewall = db.Column(db.Boolean)
    primary_browser = db.Column(db.String)
    primary_browser_version = db.Column(db.String)
    secondary_browser = db.Column(db.String)
    secondary_browser_version = db.Column(db.String)
    # PostgreSQL TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    created_at = db.Column(db.DateTime(timezone=True), default=db.func.current_timestamp())

    user = db.relationship('User', backref='responses')

    def __repr__(self):
        return f"<Response(response_id={self.response_id}, userID={self.userID}, created_at={self.created_at})>"

# One row per education choice
class ResponseEducation(db.Model):
    __tablename__ = 'response_education' # 'response_education' is lowercase in DB
    id = db.Column(db.Integer, primary_key=True) # SERIAL for PG
    response_id = db.Column(db.Integer, db.ForeignKey('responses.response_id'), nullable=False) # Table 'responses' (lowercase), column "response_id" (quoted)
    education = db.Column(db.String, nullable=False)

    response = db.relationship('Response', backref='education_choices')

    def __repr__(self):
        return f"<ResponseEducation(id={self.id}, response_id={self.response_id}, education='{self.education}')>"

# One row per OS choice + its version
class ResponseOS(db.Model):
    __tablename__ = 'response_os' # 'response_os' is lowercase in DB
    id = db.Column(db.Integer, primary_key=True) # SERIAL for PG
    response_id = db.Column(db.Integer, db.ForeignKey('responses.response_id'), nullable=False) # Table 'responses' (lowercase), column "response_id" (quoted)
    os_name = db.Column(db.String, nullable=False)
    os_version = db.Column(db.String)

    response = db.relationship('Response', backref='os_choices')

    def __repr__(self):
        return f"<ResponseOS(id={self.id}, response_id={self.response_id}, os_name='{self.os_name}', os_version='{self.os_version}')>"

# --- Session Model ---
class ActivitySessions(db.Model): # Class name as requested, maps to "Sessions" table
    __tablename__ = 'Sessions' # This is case-preserved in DB ("Sessions")

    ID = db.Column(db.Integer, primary_key=True) # SERIAL for PG
    StartTimestamp = db.Column(db.BigInteger, nullable=False)
    EndTimestamp = db.Column(db.BigInteger, nullable=False)
    DataFileName = db.Column(db.String(500), nullable=True) # Specify string length or use db.Text
    Processed = db.Column(db.Boolean, default=False) # Changed to Boolean, default=False for PG
    SessionType = db.Column(db.Integer, nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True) # Table 'users' (lowercase), column userID (quoted)

    # Specific foreign keys for each activity type (all explicitly quoted)
    StartKeyID = db.Column(db.Integer, db.ForeignKey('KeyPresses.KeyID'), nullable=True) # Table KeyPresses (quoted), column KeyID (quoted)
    EndKeyID = db.Column(db.Integer, db.ForeignKey('KeyPresses.KeyID'), nullable=True) # Table KeyPresses (quoted), column KeyID (quoted)

    StartScrollingID = db.Column(db.Integer, db.ForeignKey('Scrolling.ID'), nullable=True) # Table Scrolling (quoted), column ID (quoted)
    EndScrollingID = db.Column(db.Integer, db.ForeignKey('Scrolling.ID'), nullable=True) # Table Scrolling (quoted), column ID (quoted)

    StartMouseMovementID = db.Column(db.Integer, db.ForeignKey('MouseMovement.ID'), nullable=True) # Table MouseMovement (quoted), column ID (quoted)
    EndMouseMovementID = db.Column(db.Integer, db.ForeignKey('MouseMovement.ID'), nullable=True) # Table MouseMovement (quoted), column ID (quoted)

    ActivityID = db.Column(db.Integer, db.ForeignKey('ActivityTypes.ActivityTypeID'), nullable=True) # Table Activities (quoted), column ID (quoted)
    
    WatchOffset = db.Column(db.BigInteger, nullable=True)
    BrowserOffset = db.Column(db.BigInteger, nullable=True)

    # Relationships (backrefs updated to be more unique if not specified by you)
    user = db.relationship('User', backref='activity_sessions_for_user') # Changed backref to avoid generic 'sessions'
    start_key_press = db.relationship('KeyPress', foreign_keys=[StartKeyID], backref='activity_session_starts_key')
    end_key_press = db.relationship('KeyPress', foreign_keys=[EndKeyID], backref='activity_session_ends_key')

    start_scrolling = db.relationship('Scrolling', foreign_keys=[StartScrollingID], backref='activity_session_starts_scrolling')
    end_scrolling = db.relationship('Scrolling', foreign_keys=[EndScrollingID], backref='activity_session_ends_scrolling')

    start_mouse_movement = db.relationship('MouseMovement', foreign_keys=[StartMouseMovementID], backref='activity_session_mouse_movement_starts')
    end_mouse_movement = db.relationship('MouseMovement', foreign_keys=[EndMouseMovementID], backref='activity_session_mouse_movement_ends')

    activity = db.relationship('ActivityType', foreign_keys=[ActivityID], backref='related_activity_sessions') # Refers to the Activity model (class Activity)

    def __repr__(self):
        return (f"<ActivitySessions(ID={self.ID}, StartTimestamp={self.StartTimestamp}, EndTimestamp={self.EndTimestamp}, "
                f"SessionType={self.SessionType}, userID={self.userID})>")