from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pdfplumber
import difflib
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(pdf_file: UploadFile, start_page: int) -> List[str]:
    try:
        with pdfplumber.open(pdf_file.file) as pdf:
            text = []
            for page in pdf.pages[start_page:]:
                text.extend(page.extract_text().split('\n'))
            return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/upload/")
async def upload_files(
    file1: UploadFile = File(...), start1: int = Form(...),
    file2: UploadFile = File(...), start2: int = Form(...)):
    
    text1 = extract_text_from_pdf(file1, start1)
    text2 = extract_text_from_pdf(file2, start2)
    
    diff = list(difflib.unified_diff(text1, text2, lineterm=""))
    return {"differences": diff}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
