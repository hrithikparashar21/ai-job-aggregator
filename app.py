from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

# --- Database Connection Function ---
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# --- Route 1: Test Route ---
@app.get("/")
def read_root():
    return {"message": "Hello from AI Job Aggregator API"}

# --- Route 2: Fetch Jobs ---
@app.get("/jobs")
def get_jobs():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, title, company, location FROM jobs LIMIT 10;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        jobs = []
        for row in rows:
            jobs.append({
                "id": row[0],
                "title": row[1],
                "company": row[2],
                "location": row[3]
            })

        return {"jobs": jobs}

    except Exception as e:
        return {"error": str(e)}
