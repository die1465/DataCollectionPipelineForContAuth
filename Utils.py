# import eventlet
# eventlet.monkey_patch()

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import join_room, leave_room, send, SocketIO, emit
import random, os, json, time
from flask_sqlalchemy import SQLAlchemy
from string import ascii_uppercase
import socketio
import threading, queue
from dotenv import load_dotenv

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
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
app.config['SQLALCHEMY_DATABASE_URI'] = \
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

socketioConnection = SocketIO(app, 
                              cors_allowed_origins="*",
                              ping_interval=25,  # Default, you can keep this or slightly increase if needed
                              ping_timeout=100000,    # <--- **Increase this significantly**
                              async_mode="threading"

                            )

