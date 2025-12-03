from Utils import db, app
import datetime

# --- User Model ---
class User(db.Model):
    __tablename__ = 'users' # No need to quote if table name is lowercase in DB, but consistent with convention
    userID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<User(userID={self.userID}, name='{self.name}')>"

# --- Response Model ---
class Response(db.Model):
    __tablename__ = 'responses'
    response_id = db.Column(db.Integer, primary_key=True)
    userID = db.Column(
        db.Integer,
        db.ForeignKey('users.userID'), # Quoted foreign key reference
        nullable=False
    )
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
    ever_installed_os = db.Column(db.Boolean)
    ever_designed_website = db.Column(db.Boolean)
    ever_registered_domain = db.Column(db.Boolean)
    ever_used_telnet_ssh = db.Column(db.Boolean)
    ever_changed_firewall = db.Column(db.Boolean)
    primary_browser = db.Column(db.String)
    primary_browser_version = db.Column(db.String)
    secondary_browser = db.Column(db.String)
    secondary_browser_version = db.Column(db.String)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=db.func.current_timestamp(),
        nullable=False
    )

    user = db.relationship('User', backref='responses')
    education = db.relationship(
        'ResponseEducation', back_populates='response',
        cascade='all, delete-orphan'
    )
    os_entries = db.relationship(
        'ResponseOS', back_populates='response',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<Response(response_id={self.response_id}, userID={self.userID}, created_at={self.created_at})>"


# --- ResponseEducation Model ---
class ResponseEducation(db.Model):
    __tablename__ = 'response_education'
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(
        db.Integer,
        db.ForeignKey('responses.response_id'), # Quoted foreign key reference
        nullable=False
    )
    education = db.Column(db.String, nullable=False)

    response = db.relationship('Response', back_populates='education')

    def __repr__(self):
        return f"<ResponseEducation(id={self.id}, response_id={self.response_id}, education='{self.education}')>"

# --- ResponseOS Model ---
class ResponseOS(db.Model):
    __tablename__ = 'response_os'
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(
        db.Integer,
        db.ForeignKey('responses.response_id'), # Quoted foreign key reference
        nullable=False
    )
    os_name = db.Column(db.String, nullable=False)
    os_version = db.Column(db.String)

    response = db.relationship('Response', back_populates='os_entries')

    def __repr__(self):
        return f"<ResponseOS(id={self.id}, response_id={self.response_id}, os_name='{self.os_name}', os_version='{self.os_version}')>"

# --- KeyPress Model ---
class KeyPress(db.Model):
    __tablename__ = 'KeyPresses'
    KeyID = db.Column(db.Integer, primary_key=True)
    KeyDownTimestamp = db.Column(db.BigInteger, nullable=False)
    KeyPressed = db.Column(db.String, nullable=False)
    KeyUpTimestamp = db.Column(db.BigInteger, nullable=False)
    AudioFileName = db.Column(db.String(500), nullable=True)
    SensorFileName = db.Column(db.String(500), nullable=True)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True) # Quoted foreign key reference

    user = db.relationship('User', backref='key_presses')

    def __repr__(self):
        return (f"<KeyPresses(KeyID={self.KeyID}, KeyDownTimestamp={self.KeyDownTimestamp}, "
                f"KeyUpTimestamp={self.KeyUpTimestamp}, KeyPressed={self.KeyPressed}, "
                f"AudioFileName={self.AudioFileName}, SensorFileName={self.SensorFileName}, userID={self.userID})>")

# --- Scrolling Model ---
class Scrolling(db.Model):
    __tablename__ = 'Scrolling'
    ID = db.Column(db.Integer, primary_key=True)
    StartTimestamp = db.Column(db.BigInteger, nullable=False)
    EndTimestamp = db.Column(db.BigInteger, nullable=False)
    DataFileName = db.Column(db.String(500), nullable=True)
    Direction = db.Column(db.Integer, nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True) # Quoted foreign key reference

    user = db.relationship('User', backref='scrolls')

    def __repr__(self):
        return (f"<Scrolling(ID={self.ID}, StartTimestamp={self.StartTimestamp}, "
                f"EndTimestamp={self.EndTimestamp}, DataFileName={self.DataFileName}, "
                f"Direction={self.Direction}, userID={self.userID})>")
    
# --- MouseMovement Model ---
class MouseMovement(db.Model):
    __tablename__ = 'MouseMovement'
    ID = db.Column(db.Integer, primary_key=True)
    StartTimestamp = db.Column(db.BigInteger, nullable=False)
    EndTimestamp = db.Column(db.BigInteger, nullable=False)
    DataFileName = db.Column(db.String(500), nullable=True)
    Direction = db.Column(db.Integer, nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True) # Quoted foreign key reference

    user = db.relationship('User', backref='mouse_movements')

    def __repr__(self):
        return (f"<MouseMovement(ID={self.ID}, StartTimestamp={self.StartTimestamp}, "
                f"EndTimestamp={self.EndTimestamp}, DataFileName={self.DataFileName}, "
                f"Direction={self.Direction}, userID={self.userID})>")

# --- ActivityType Model ---
class ActivityType(db.Model):
    __tablename__ = 'ActivityTypes'
    ActivityTypeID = db.Column(db.Integer, primary_key=True)
    ActivityName = db.Column(db.String, nullable=False, unique=True)

    def __repr__(self):
        return f"<ActivityType(ActivityTypeID={self.ActivityTypeID}, ActivityName='{self.ActivityName}')>"

# --- Activities Model (RENAMED from Activities as `Activities` was causing confusion and model names are typically singular) ---
class Activity(db.Model): # RENAMED for clarity and consistency
    __tablename__ = 'Activities' # Table name remains "Activities"
    ID = db.Column(db.Integer, primary_key=True)
    StartTimestamp = db.Column(db.BigInteger, nullable=False)
    EndTimestamp = db.Column(db.BigInteger, nullable=False)
    
    ActivityTypeID = db.Column(db.Integer, db.ForeignKey('ActivityTypes.ActivityTypeID'), nullable=False) # Quoted foreign key reference
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True) # Quoted foreign key reference

    user = db.relationship('User', backref='activities')
    activity_type = db.relationship('ActivityType', backref='activities_relation') # Changed backref name to avoid potential conflict

    def __repr__(self):
        return (
            f"<Activity(ID={self.ID}, StartTimestamp={self.StartTimestamp}, "
            f"EndTimestamp={self.EndTimestamp}, ActivityTypeID={self.ActivityTypeID}, userID={self.userID})>"
        )

# --- Messages Model ---
class Message(db.Model):
    __tablename__ = 'Messages'
    MessageID = db.Column(db.Integer, primary_key=True)
    SentTimestamp = db.Column(db.BigInteger, nullable=False)
    MessageContent = db.Column(db.Text, nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=False) # Quoted foreign key reference
    StartKeyID = db.Column(db.Integer, db.ForeignKey('KeyPresses.KeyID'), nullable=True) # Quoted foreign key reference
    EndKeyID = db.Column(db.Integer, db.ForeignKey('KeyPresses.KeyID'), nullable=True) # Quoted foreign key reference
    
    user = db.relationship('User', backref='messages')
    start_key = db.relationship('KeyPress', foreign_keys=[StartKeyID], backref='start_messages')
    end_key = db.relationship('KeyPress', foreign_keys=[EndKeyID], backref='end_messages')

    def __repr__(self):
        return (f"<Message(MessageID={self.MessageID}, SentTimestamp={self.SentTimestamp}, "
                f"MessageContent='{self.MessageContent[:50]}...', userID={self.userID}, "
                f"StartKeyID={self.StartKeyID}, EndKeyID={self.EndKeyID})>")

# --- Session Model (RENAMED from ActivitySessions for clarity and consistency) ---
class Session(db.Model): # RENAMED from ActivitySessions
    __tablename__ = 'Sessions' # Table name remains "Sessions"

    ID = db.Column(db.Integer, primary_key=True)
    StartTimestamp = db.Column(db.BigInteger, nullable=False)
    EndTimestamp = db.Column(db.BigInteger, nullable=False)
    DataFileName = db.Column(db.String(500), nullable=True)
    Processed = db.Column(db.Boolean, default=False)
    SessionType = db.Column(db.Integer, nullable=False)
    userID = db.Column(db.Integer, db.ForeignKey('users.userID'), nullable=True) # Quoted foreign key reference

    # Specific foreign keys (all quoted)
    StartKeyID = db.Column(db.Integer, db.ForeignKey('KeyPresses.KeyID'), nullable=True)
    EndKeyID = db.Column(db.Integer, db.ForeignKey('KeyPresses.KeyID'), nullable=True)

    StartScrollingID = db.Column(db.Integer, db.ForeignKey('Scrolling.ID'), nullable=True)
    EndScrollingID = db.Column(db.Integer, db.ForeignKey('Scrolling.ID'), nullable=True)

    StartMouseMovementID = db.Column(db.Integer, db.ForeignKey('MouseMovement.ID'), nullable=True)
    EndMouseMovementID = db.Column(db.Integer, db.ForeignKey('MouseMovement.ID'), nullable=True)

    ActivityID = db.Column(db.Integer, db.ForeignKey('ActivityTypes.ActivityTypeID'), nullable=True) # Quoted foreign key reference to the "Activities" table
    
    WatchOffset = db.Column(db.BigInteger, nullable=True)
    BrowserOffset = db.Column(db.BigInteger, nullable=True)

    # Relationships
    user = db.relationship('User', backref='sessions_relation') # Changed backref to avoid conflict
    start_key_press = db.relationship('KeyPress', foreign_keys=[StartKeyID], backref='session_starts_key')
    end_key_press = db.relationship('KeyPress', foreign_keys=[EndKeyID], backref='session_ends_key')

    start_scrolling = db.relationship('Scrolling', foreign_keys=[StartScrollingID], backref='session_starts_scrolling')
    end_scrolling = db.relationship('Scrolling', foreign_keys=[EndScrollingID], backref='session_ends_scrolling')

    start_mouse_movement = db.relationship('MouseMovement', foreign_keys=[StartMouseMovementID], backref='session_starts_mouse')
    end_mouse_movement = db.relationship('MouseMovement', foreign_keys=[EndMouseMovementID], backref='session_ends_mouse')

    activity = db.relationship('ActivityType', foreign_keys=[ActivityID], backref='session_activities') # Refers to the Activity model

    def __repr__(self):
        return (f"<Session(ID={self.ID}, StartTimestamp={self.StartTimestamp}, EndTimestamp={self.EndTimestamp}, "
                f"SessionType={self.SessionType}, userID={self.userID})>")


# --- DBInteractions Class ---
class DBInteractions:
    @staticmethod
    def UserNameExistsInDatabase(username):
        with app.app_context():
            return User.query.filter_by(name=username).first() is not None

    @staticmethod
    def GetUserID(username):
        with app.app_context():
            user = User.query.filter_by(name=username).first()
            return user.userID if user else None

    @staticmethod
    def GetUserByID(ID: int):
        with app.app_context():
            return User.query.filter_by(userID=ID).first()

    @staticmethod
    def AddUserToDatabase(name):
        with app.app_context():
            if DBInteractions.UserNameExistsInDatabase(name):
                print("User already exists in DB")
            else:
                Newuser = User(name=name)
                db.session.add(Newuser)
                try:
                    db.session.commit()
                    print("added ", name, " successfully")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error adding user {name}: {e}")