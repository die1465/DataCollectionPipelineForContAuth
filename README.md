# Data-Collection-Pipeline-For-Continuous-Authentication (Early Access)

This was the data collection pipeline for WACWAC (Wearable Assisted Continuous Web Authentication through Multimodal Correlation)


prerequisites:

having docker desktop installed
having uv installed



to install dependencies:

uv pip install -r requirements.lock


for setting up the database:
don't forget to configure the .env for the DB credentials

we use a postgres DB in a docker container, to setup the DB:
docker compose up -d db
then uv run createDB.py to create the tables in the database




The main.py is the web server

the WatchServer.py is the watch API

the Services.py is the preprocessing services API

run watchServer and services before main.py

# 💾 Data Collection Pipeline for Continuous Authentication

This repository contains the data collection pipeline for WACWAC (Wearable Assisted Continuous Web Authentication through Multimodal Correlation).

---

## 🛠️ Prerequisites

Before getting started, you'll need the following tools installed on your system:

* Docker Desktop (for running the PostgreSQL database container).
* uv (a fast Python package installer and environment manager).

---

## 🚀 Setup and Installation

Follow these steps to set up the project environment and database.

### 1. Dependency Installation

We use the locked file, **`requirements.lock`**, to ensure a reproducible environment across all systems.

1.  **Create a Virtual Environment:**
    ```bash
    uv venv
    ```
2.  **Activate the Environment:**
    * **macOS/Linux:** `source .venv/bin/activate`
    
3.  **Install Dependencies:**
    ```bash
    uv pip install -r requirements.lock
    ```

### 2. Database Setup (PostgreSQL)

This project uses a PostgreSQL database running in a Docker container.

1.  **Configure Credentials:**
    * Create a **`.env`** file in the root directory.
    * **configure the database credentials** in this file (e.g., `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) to match what is configured in your `docker-compose.yml`.

2.  **Start the Database Container:**
    ```bash
    docker compose up -d db
    ```
    This command starts the database container in the background.

3.  **Create Database Tables:**
    Once the container is running, execute the table creation script:
    ```bash
    uv run createDB.py
    ```

---

## ▶️ Running the Pipeline

The pipeline consists of three main components that must be run in a specific order.

1.  **Start Background Services (Prerequisite)**
    These services must be running before the main web server starts, as they handle data processing and the wearable API.

    * **Watch API Server:**
        ```bash
        uv run WatchServer.py
        ```
    * **Preprocessing Service API:**
        ```bash
        uv run Services.py
        ```
    

2.  **Start the Main Web Server**
    This is the core application server that handles website.

    ```bash
    uv run main.py
    ```

**all the collected data is stored in SessionsData/**
---

## 📊 Data Analysis and Visualization

The **`Data Analysis.ipynb`** Jupyter Notebook is provided for exploring the collected data.

This notebook demonstrates how to:

* Load and query data from the PostgreSQL database.
* **Visualize a typing session** over the **typing timestamps** captured from the browser.

To run this notebook, ensure your database is running and then launch Jupyter