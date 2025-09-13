from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi.responses import RedirectResponse

app = FastAPI(title="AI Job Aggregator API")

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Redirect root (/) → frontend
@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("PGHOST"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        port=os.getenv("PGPORT"),
        cursor_factory=RealDictCursor
    )
    return conn

# Job model
class Job(BaseModel):
    title: str
    company: str | None = None
    location: str | None = None
    description: str | None = None

# Get jobs
@app.get("/jobs")
def get_jobs():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY created_at DESC;")
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    return jobs

# Add job
@app.post("/add-job")
def add_job(job: Job):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO jobs (title, company, location, description) VALUES (%s, %s, %s, %s) RETURNING *;",
        (job.title, job.company, job.location, job.description)
    )
    new_job = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {"inserted": new_job}
