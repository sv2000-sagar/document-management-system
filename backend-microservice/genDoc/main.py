# main.py

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import datetime
from docxtpl import DocxTemplate
from fastapi.responses import FileResponse
from fastapi import Path as FastAPIPath

import schemas

app = FastAPI()

# CORS settings
origins = [
    "http://localhost:3000",  # React development server
    "http://127.0.0.1:3000",
    # Add other origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specific origins or use ["*"] for all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to save generated documents
GENERATED_DOCS_DIR = Path(__file__).parent / "generated_docs"
GENERATED_DOCS_DIR.mkdir(exist_ok=True)  # Create the directory if it doesn't exist

@app.post("/gen_doc")
def gen_doc(doc_req: schemas.DocGen):
    print(doc_req)
    template_path = Path(__file__).parent / "vendor-contract.docx"
    doc = DocxTemplate(template_path)

    non_refundable = round(doc_req.amount * 0.2, 2)
    today = datetime.datetime.today()
    today_in_one_week = today + datetime.timedelta(days=7)

    context = {
        "CLIENT": doc_req.client,
        "VENDOR": doc_req.vendor,
        "LINE1": doc_req.line1,
        "LINE2": doc_req.line2,
        "AMOUNT": doc_req.amount,
        "NONREFUNDABLE": non_refundable,
        "TODAY": today.strftime("%Y-%m-%d"),
        "TODAY_IN_ONE_WEEK": today_in_one_week.strftime("%Y-%m-%d"),
    }

    doc.render(context)

    # Generate a unique filename
    filename = f"{doc_req.vendor}-contract-{int(datetime.datetime.now().timestamp())}.docx"
    file_path = GENERATED_DOCS_DIR / filename

    # Save the generated document
    doc.save(file_path)

    # Construct the download URL
    download_url = f"/download/{filename}"

    # Return the download link to the frontend
    return {"download_url": download_url}

@app.get("/download/{filename}")
def download_file(filename: str = FastAPIPath(..., description="The name of the file to download")):
    # Ensure filename is secure
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = GENERATED_DOCS_DIR / filename

    # Check if file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Serve the file
    return FileResponse(
        path=file_path,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=filename,
    )
