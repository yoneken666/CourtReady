CourtReady Project Setup Guide

This guide covers the complete setup for the FastAPI Backend, React Frontend, and PostgreSQL Database to run the CourtReady application.

1. Prerequisites

Before you begin, make sure you have the following software installed on your system:

Python 3.10+

Node.js & npm

PostgreSQL (You can download it from postgresql.org)

PyCharm (Recommended IDE)

2. Database Setup

You must install and configure the database before running the backend.

Install PostgreSQL: Follow the installer. When it asks you to set a password for the postgres user, remember what you set.

Create the Database:

Open pgAdmin (which installs with PostgreSQL).

Connect to your local server (using the password you just set).

In the browser panel, right-click Databases > Create > Database...

Enter the database name exactly: courtready_db

Click Save.

3. Backend Setup (FastAPI)

All commands are run from the practise/backend directory.

Step 3.1: Create & Activate Virtual Environment

Open your terminal and navigate to the backend folder:

cd practise/backend

Create and activate the virtual environment (.venv):

python -m venv .venv

.\.venv\Scripts\activate

(Your terminal prompt should now show (.venv))

Step 3.2: Configure Database Connection

Open the file practise/backend/database.py in PyCharm.

Find this line:

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost/courtready_db"

Replace YOUR_POSTGRES_PASSWORD with the actual password you set during the PostgreSQL installation.

Step 3.3: Install All Python Dependencies

Run these commands one by one. We are installing specific versions of bcrypt and passlib to prevent a known login/signup compatibility error.

Install core libraries

pip install fastapi "uvicorn[standard]" python-multipart sqlalchemy psycopg2-binary python-jose[cryptography] email-validator

Install specific, compatible versions for auth

pip uninstall -y passlib bcrypt

pip install bcrypt==4.0.1

pip install passlib


Step 3.4: Run the Backend Server

Start the FastAPI server. On its first successful run, it will automatically create the users table in your database.

uvicorn main:app --reload


Keep this terminal open and running.

4. Frontend Setup (React)

Use a NEW terminal window for these commands.

Step 4.1: Install Node Dependencies

Navigate to the frontend folder:

cd practise/frontend


Install all required packages (React, Axios, etc.):

npm install

npm install axios

npm install react-router-dom


Step 4.2: Run the Frontend Application

Start the React development server.

npm run dev


Keep this terminal open and running.

5. Launch the App

Open the URL provided by the frontend terminal (e.g., http://localhost:5173) in your web browser. You can now sign up for a new account, log in, and use the application.
