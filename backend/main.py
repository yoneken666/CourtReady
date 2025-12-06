import uvicorn
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import pypdf
import docx

import models, schemas, auth
from database import engine, get_db
# --- IMPORT AI SERVICE ---
from ai_service import ai_system

models.Base.metadata.create_all(bind=engine)

app = FastAPI(debug=True)

# ... (CORS and UPLOAD_DIRECTORY remain the same) ...
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


# ... (Text extraction helper and Auth endpoints remain the same) ...
def extract_text_from_file(file_path: str, content_type: str) -> str:
    text = ""
    try:
        if "pdf" in content_type or file_path.endswith(".pdf"):
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        elif "word" in content_type or "officedocument" in content_type or file_path.endswith(".docx"):
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        else:
            return ""
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""
    return text


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
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# --- UPDATED: Protected Case Endpoint with AI ---

@app.post("/api/case", response_model=schemas.CaseResponse)
def create_case(
        case_details: schemas.CaseIntake,
        current_user: dict = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == current_user['email']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 1. Save Case to DB
    new_case = models.Case(
        title=case_details.caseTitle,
        case_type=case_details.caseType,
        description=case_details.caseDescription,
        user_id=user.id
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    # 2. RUN AI ANALYSIS
    # We combine title + description for the AI query
    query_text = f"{case_details.caseTitle} {case_details.caseDescription}"
    ai_result = ai_system.analyze_case(query_text)

    # 3. Return combined response
    return {
        "caseTitle": new_case.title,
        "caseType": new_case.case_type,
        "caseDescription": new_case.description,
        "id": new_case.id,
        "owner_email": user.email,
        "ai_analysis": ai_result
    }


# ... (Upload documents endpoint remains same as previous version) ...
@app.post("/api/upload-documents")
def upload_documents(
        case_id: int = Form(...),
        files: List[UploadFile] = File(...),
        current_user: dict = Depends(auth.get_current_user),
        db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == current_user['email']).first()
    case = db.query(models.Case).filter(models.Case.id == case_id, models.Case.user_id == user.id).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found or unauthorized")

    saved_files = []

    for file in files:
        allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        if file.content_type not in allowed_types and not file.filename.endswith(('.pdf', '.docx')):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Please upload only Word (.docx) or PDF documents."
            )

        file_path = os.path.join(UPLOAD_DIRECTORY, f"case_{case_id}_{file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extracted_text = extract_text_from_file(file_path, file.content_type)

        new_doc = models.Document(
            filename=file.filename,
            file_path=file_path,
            extracted_text=extracted_text,
            case_id=case.id
        )
        db.add(new_doc)
        saved_files.append({"filename": file.filename, "extracted_chars": len(extracted_text)})

    db.commit()
    return {"status": "success", "saved_files": saved_files}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)