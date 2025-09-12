import os
import uuid
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
import pdfplumber
import docx2txt

# ----- Config from env -----
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY environment variables")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="AI Job Aggregator - Starter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this for production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello, world!"}

@app.get("/jobs/list")
async def list_jobs(limit: int = 50):
    res = supabase.table("jobs").select("*").order("created_at", {"ascending": False}).limit(limit).execute()
    if res.get("error"):
        raise HTTPException(status_code=500, detail=str(res["error"]))
    return res.get("data", [])

@app.post("/jobs/add")
async def add_job(job: dict):
    res = supabase.table("jobs").insert(job).execute()
    if res.get("error"):
        raise HTTPException(status_code=500, detail=str(res["error"]))
    return {"status": "ok", "inserted": res.get("data")}

@app.post("/cv/upload")
async def upload_cv(user_id: str = Form(None), file: UploadFile = File(...)):
    # Save uploaded file to temp
    suffix = os.path.splitext(file.filename)[1].lower()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    data = await file.read()
    tmp.write(data)
    tmp.flush()
    tmp.close()

    # Extract text (simple)
    text = ""
    try:
        if suffix == ".pdf":
            with pdfplumber.open(tmp.name) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
                text = "\n".join(pages)
        elif suffix in [".docx", ".doc"]:
            text = docx2txt.process(tmp.name)
        else:
            try:
                text = data.decode("utf-8", errors="ignore")
            except:
                text = ""
    except Exception as e:
        text = ""

    # Simple skill extraction (starter list)
    SKILLS = ["python","django","flask","sql","postgres","javascript","react","node","aws","docker","kubernetes","java","c++","html","css"]
    found = [s for s in SKILLS if s in text.lower()]

    # Upload raw file to Supabase storage (bucket: 'cvs')
    bucket = supabase.storage().from_("cvs")
    remote_path = f"{uuid.uuid4()}_{file.filename}"
    with open(tmp.name, "rb") as f:
        upload_resp = bucket.upload(remote_path, f)
    # Make sure your bucket is public or create signed URL in Prod
    public_info = bucket.get_public_url(remote_path)
    public_url = None
    if isinstance(public_info, dict):
        public_url = public_info.get("publicURL") or public_info.get("public_url")
    else:
        # if library returns object, attempt attribute access
        public_url = getattr(public_info, "publicURL", None) or getattr(public_info, "public_url", None)

    # Save parsed CV to DB
    record = {
        "user_id": user_id,
        "original_file_url": public_url,
        "parsed_skills": found,
        "parsed_roles": [],
        "parsed_location": [],
        "experience_years": None
    }
    res = supabase.table("user_cvs").insert(record).execute()
    if res.get("error"):
        raise HTTPException(status_code=500, detail=str(res["error"]))

    return {"status": "ok", "parsed_skills": found, "file_url": public_url}
