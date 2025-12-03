import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# --- Database Connection Details (from your docker-compose.yml and .env) ---
DB_NAME = os.getenv('POSTGRES_DB', 'mydatabase')
DB_USER = os.getenv('POSTGRES_USER', 'myuser')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'mypassword')
DB_HOST = os.getenv('DB_HOST', 'localhost') # Or 'db' if running from another container in the same compose network
DB_PORT = os.getenv('DB_PORT', '5432')

try:
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    # Set isolation level to allow DDL statements immediately
    conn.autocommit = True # For DROP TABLE to work independently

    # --- Drop tables in reverse order of dependency ---
    # This ensures you can recreate them cleanly without foreign key constraint issues
    print("Dropping existing tables if they exist...")
    # Quoting table names for consistency
    cursor.execute('DROP TABLE IF EXISTS "Sessions" CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS "Activities" CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS "ActivityTypes" CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS "MouseMovement" CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS "Scrolling" CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS "Messages" CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS "KeyPresses" CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS "response_os" CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS "response_education" CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS "responses" CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS "users" CASCADE;') # This was already lowercase, but quoting it for explicit consistency
    print("Tables dropped.")


    # Reset autocommit to False for transaction block
    conn.autocommit = False
    
    # --- Create tables ---
    print("Creating tables...")

    # "users" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "users" (
        "userID" SERIAL PRIMARY KEY,  -- Quoted
        "name" TEXT NOT NULL        -- Quoted
    );
    ''')

    # "responses" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "responses" (
        "response_id"               SERIAL PRIMARY KEY, -- Quoted
        "userID"                    INTEGER    NOT NULL, -- Quoted
        "age"                       INTEGER, -- Quoted
        "gender"                    TEXT,    -- Quoted
        "field_of_study"            TEXT,    -- Quoted
        "occupation"                TEXT,    -- Quoted
        "hours_per_week"            INTEGER, -- Quoted
        "primary_language"          TEXT,    -- Quoted
        "shop_online_frequency"     TEXT,    -- Quoted
        "online_banking_frequency"  TEXT,    -- Quoted
        "ebay_usage"                TEXT,    -- Quoted
        "amazon_usage"              TEXT,    -- Quoted
        "paypal_usage"              TEXT,    -- Quoted
        "bank_usage"                TEXT,    -- Quoted
        "ever_installed_os"         BOOLEAN, -- Quoted
        "ever_designed_website"     BOOLEAN, -- Quoted
        "ever_registered_domain"    BOOLEAN, -- Quoted
        "ever_used_telnet_ssh"      BOOLEAN, -- Quoted
        "ever_changed_firewall"     BOOLEAN, -- Quoted
        "primary_browser"           TEXT,    -- Quoted
        "primary_browser_version"   TEXT,    -- Quoted
        "secondary_browser"         TEXT,    -- Quoted
        "secondary_browser_version" TEXT,    -- Quoted
        "created_at"                TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Quoted
        FOREIGN KEY ("userID") REFERENCES "users"("userID") -- Quoted foreign key references
    );
    ''')

    # "response_education" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "response_education" (
        "id"            SERIAL PRIMARY KEY, -- Quoted
        "response_id"   INTEGER    NOT NULL, -- Quoted
        "education"     TEXT       NOT NULL, -- Quoted
        FOREIGN KEY ("response_id") REFERENCES "responses"("response_id") -- Quoted foreign key reference
    );
    ''')

    # "response_os" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "response_os" (
        "id"            SERIAL PRIMARY KEY, -- Quoted
        "response_id"   INTEGER    NOT NULL, -- Quoted
        "os_name"       TEXT       NOT NULL, -- Quoted
        "os_version"    TEXT,    -- Quoted
        FOREIGN KEY ("response_id") REFERENCES "responses"("response_id") -- Quoted foreign key reference
    );
    ''')

    # "KeyPresses" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "KeyPresses"(
        "KeyID" SERIAL PRIMARY KEY, -- Quoted
        "KeyDownTimestamp" BIGINT NOT NULL, -- Quoted
        "KeyPressed" TEXT NOT NULL, -- Quoted
        "KeyUpTimestamp" BIGINT NOT NULL, -- Quoted
        "AudioFileName" TEXT, -- Quoted
        "SensorFileName" TEXT, -- Quoted
        "userID" INTEGER, -- Quoted
        FOREIGN KEY ("userID") REFERENCES "users"("userID") -- Quoted foreign key reference
    );
    ''')

    # "Messages" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "Messages"(
        "MessageID" SERIAL PRIMARY KEY, -- Quoted
        "SentTimestamp" BIGINT NOT NULL, -- Quoted
        "MessageContent" TEXT NOT NULL, -- Quoted
        "userID" INTEGER NOT NULL, -- Quoted
        "StartKeyID" INTEGER, -- Quoted
        "EndKeyID" INTEGER, -- Quoted
        FOREIGN KEY ("userID") REFERENCES "users"("userID"), -- Quoted
        FOREIGN KEY ("StartKeyID") REFERENCES "KeyPresses"("KeyID"), -- Quoted
        FOREIGN KEY ("EndKeyID") REFERENCES "KeyPresses"("KeyID") -- Quoted
    );
    ''')

    # "Scrolling" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "Scrolling"(
        "ID" SERIAL PRIMARY KEY, -- Quoted
        "StartTimestamp" BIGINT NOT NULL, -- Quoted
        "EndTimestamp" BIGINT NOT NULL, -- Quoted
        "DataFileName" TEXT, -- Quoted
        "Direction" INTEGER NOT NULL, -- Quoted
        "userID" INTEGER, -- Quoted
        FOREIGN KEY ("userID") REFERENCES "users"("userID") -- Quoted
    );
    ''')

    # "MouseMovement" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "MouseMovement"(
        "ID" SERIAL PRIMARY KEY, -- Quoted
        "StartTimestamp" BIGINT NOT NULL, -- Quoted
        "EndTimestamp" BIGINT NOT NULL, -- Quoted
        "DataFileName" TEXT, -- Quoted
        "Direction" INTEGER NOT NULL, -- Quoted
        "userID" INTEGER, -- Quoted
        FOREIGN KEY ("userID") REFERENCES "users"("userID") -- Quoted
    );
    ''')

    # "ActivityTypes" table
    cursor.execute('''
    CREATE TABLE "ActivityTypes" ( -- Quoted table name
        "ActivityTypeID" SERIAL PRIMARY KEY, -- Quoted
        "ActivityName" TEXT NOT NULL UNIQUE -- Quoted
    );
    ''')

    # "Activities" table
    cursor.execute('''
    CREATE TABLE "Activities" ( -- Quoted table name
        "ID" SERIAL PRIMARY KEY, -- Quoted
        "StartTimestamp" BIGINT NOT NULL, -- Quoted
        "EndTimestamp" BIGINT NOT NULL, -- Quoted
        "ActivityTypeID" INTEGER NOT NULL, -- Quoted
        "userID" INTEGER, -- Quoted
        FOREIGN KEY ("ActivityTypeID") REFERENCES "ActivityTypes"("ActivityTypeID"), -- Quoted
        FOREIGN KEY ("userID") REFERENCES "users"("userID") -- Quoted
    );
    ''')

    # "Sessions" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS "Sessions"(
        "ID" SERIAL PRIMARY KEY, -- Quoted
        "StartTimestamp" BIGINT NOT NULL, -- Quoted
        "EndTimestamp" BIGINT NOT NULL, -- Quoted
        "DataFileName" TEXT, -- Quoted
        "Processed" BOOLEAN DEFAULT FALSE, -- Quoted
        "SessionType" INTEGER NOT NULL, -- Quoted
        "userID" INTEGER, -- Quoted
        
        -- Specific foreign keys for each activity type (all quoted)
        "StartKeyID" INTEGER,
        "EndKeyID" INTEGER,
        "StartScrollingID" INTEGER,
        "EndScrollingID" INTEGER,
        "StartMouseMovementID" INTEGER,
        "EndMouseMovementID" INTEGER,
        "ActivityID" INTEGER,
        
        "WatchOffset" BIGINT, -- Quoted
        "BrowserOffset" BIGINT, -- Quoted

        FOREIGN KEY ("userID") REFERENCES "users"("userID"), -- Quoted
        FOREIGN KEY ("StartKeyID") REFERENCES "KeyPresses"("KeyID"), -- Quoted
        FOREIGN KEY ("EndKeyID") REFERENCES "KeyPresses"("KeyID"), -- Quoted
        FOREIGN KEY ("StartScrollingID") REFERENCES "Scrolling"("ID"), -- Quoted
        FOREIGN KEY ("EndScrollingID") REFERENCES "Scrolling"("ID"), -- Quoted
        FOREIGN KEY ("StartMouseMovementID") REFERENCES "MouseMovement"("ID"), -- Quoted
        FOREIGN KEY ("EndMouseMovementID") REFERENCES "MouseMovement"("ID"), -- Quoted
        FOREIGN KEY ("ActivityID") REFERENCES "ActivityTypes"("ActivityTypeID") -- Quoted
    );
    ''')

    # Create indexes for better query performance (all quoted)
    print("Creating indexes...")
    cursor.execute('CREATE INDEX IF NOT EXISTS "idx_messages_user" ON "Messages"("userID");')
    cursor.execute('CREATE INDEX IF NOT EXISTS "idx_messages_timestamp" ON "Messages"("SentTimestamp");')
    cursor.execute('CREATE INDEX IF NOT EXISTS "idx_keypresses_timestamp" ON "KeyPresses"("KeyDownTimestamp");')
    print("Indexes created.")

    # Commit the changes and close the connection
    conn.commit()
    print("Database schema created successfully in PostgreSQL with quoted identifiers!")

except psycopg2.Error as e:
    print(f"Error connecting to or creating schema in PostgreSQL: {e}")
    if conn:
        conn.rollback() # Rollback in case of errors
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()