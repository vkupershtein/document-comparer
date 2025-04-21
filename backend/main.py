"""
Entry for FastAPI backend
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routers import compare

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

app.include_router(compare.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
