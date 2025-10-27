import uvicorn
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm  # For login form
from sqlalchemy.orm import Session
from typing import List
import os
import shutil

# Import all the new modules
# --- FIX: Changed relative imports (from . import) to direct imports ---
import models, schemas, auth
from database import engine, get_db

# This command creates your "users" table in the database
models.Base.metadata.create_all(bind=engine)

app = FastAPI(debug=True)

# --- CORS Middleware (No changes) ---
origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIRECTORY = "./uploaded_files"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)


# --- AUTHENTICATION ENDPOINTS ---

@app.post("/api/signup", status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}


@app.post("/api/token", response_model=schemas.Token)
def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# --- PROTECTED ENDPOINTS ---

@app.post("/api/case")
def create_case(
        case_details: schemas.CaseIntake,
        current_user: dict = Depends(auth.get_current_user)  # This protects the route
):
    # current_user contains {"email": "user@example.com"}
    print(f"Case created by user: {current_user['email']}")
    print("Received Case Details:")
    print(case_details.model_dump_json(indent=2))
    return {"status": "success", "data": case_details, "owner": current_user['email']}


@app.post("/api/upload-documents")
def upload_documents(
        files: List[UploadFile] = File(...),
        current_user: dict = Depends(auth.get_current_user)  # This protects the route
):
    print(f"Files uploaded by user: {current_user['email']}")
    saved_files = []
    for file in files:
        file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file.filename)

    return {"status": "success", "saved_files": saved_files}


# --- Run the App ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

