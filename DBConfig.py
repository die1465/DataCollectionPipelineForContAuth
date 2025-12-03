import psycopg2
import os
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Database Connection Details from .env
DB_NAME = os.getenv('POSTGRES_DB', 'mydatabase')
DB_USER = os.getenv('POSTGRES_USER', 'myuser')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'mypassword')
DB_HOST = os.getenv('DB_HOST', 'localhost') # 'localhost' if running on host, 'db' if from another Docker container
DB_PORT = os.getenv('DB_PORT', '5432')


