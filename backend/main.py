import logging
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uvicorn

from use_cases.processor_factory import detect_file_type
from use_cases import compare_documents
from schemas import CompareRequest, CompareResponse

logging.basicConfig(level=logging.INFO)

pdf_logger = logging.getLogger("pdfminer")
pdf_logger.setLevel(logging.ERROR)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload/")
async def upload_files(header_left: int = Form(40), footer_left: int = Form(40), 
                       size_weight_left: float = Form(0.8), header_right: int = Form(40),
                       footer_right: int = Form(40), size_weight_right: float = Form(0.8),
                       ratio_threshold: float = Form(0.5), length_threshold: int = Form(30),
                       text_column_left: str = Form(''), text_column_right: str = Form(''),
                       id_column_left: str = Form(''), id_column_right: str = Form(''), 
                       left_file: UploadFile = File(...), 
                       right_file: UploadFile = File(...)) -> CompareResponse:
    
    left_file_type = detect_file_type(left_file)
    right_file_type = detect_file_type(right_file)
    
    comparison = compare_documents(left_file.file,
                                   left_file_type, 
                                   right_file.file,
                                   right_file_type, 
                                   CompareRequest(header_left=header_left, 
                                                  header_right=header_right,
                                                  footer_left=footer_left,
                                                  footer_right=footer_right,
                                                  size_weight_left=size_weight_left,
                                                  size_weight_right=size_weight_right,
                                                  ratio_threshold=ratio_threshold,
                                                  length_threshold=length_threshold,
                                                  text_column_left=text_column_left,
                                                  text_column_right=text_column_right,
                                                  id_column_left=id_column_left,
                                                  id_column_right=id_column_right), 
                                    "json")

    comparison = (pd.DataFrame.from_records(comparison)
                          .fillna("")
                          .sort_values(["position", "position_secondary"])
                          .drop(columns=["position", "position_secondary"])
                          ).to_dict("records")        
    return CompareResponse(comparison = comparison) # type: ignore

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
