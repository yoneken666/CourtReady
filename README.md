This guide covers setting up the **FastAPI Backend** and **React Frontend** and the database:

 1\. Prerequisites

Make sure you have the following installed:

pycharm IDE (recommended)
Python 3.10+
Node.js & npm
postgresSql

2\. Backend Setup (FastAPI)

All the commands below should be run on the terminal from the `practise/backend` directory.

pip install email-validator
pip install sqlalchemy psycopg2-binary passlib[bcrypt] python-jose[cryptography]

Step 2.1: Initialize Python Environment

1.  Navigate to the backend folder:
    cd practise/backend

2.  Create/activate the virtual environment (`.venv`):
   python -m venv .venv (skip if env created already)
   .\.venv\Scripts\activate


 Step 2.2: Install All Dependencies

 Install the core web framework, server, and file-handling libraries:
 pip install fastapi uvicorn[standard] python-multipart


Step 2.3: Run the Backend Server
Start the FastAPI server. Keep this terminal window open.

cd backend
uvicorn main:app --reload

install postgres (server password is neoaspect777)

3\. Frontend Setup (React)

All commands should be run from the `practise/frontend` directory. Use a **NEW terminal window**.

Step 3.1: Install Node Dependencies
#1.  Navigate to the frontend folder:

cd practise/frontend

2.  Install all required Node packages:
npm install

Step 3.2: Run the Frontend Application

Start the React development server:
npm run dev


Step 3.3: Launch

Open the URL provided by the terminal (e.g., `http://localhost:5173`) in your web browser. The app is now fully functional.


my account password: Neo@spect777

fix ver compatibility error casuing signup/login issues:
pip uninstall passlib bcrypt
pip install bcrypt==4.0.1
pip install passlib
