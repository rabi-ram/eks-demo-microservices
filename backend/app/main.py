from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from prometheus_client import Counter, generate_latest
import boto3
import os
import io

app = FastAPI(title="EKS Demo Backend", version="2.0")

REQUEST_COUNTER = Counter("http_requests_total", "Total HTTP Requests")

REGION = os.getenv("AWS_REGION")
BUCKET = os.getenv("S3_BUCKET")

s3 = boto3.client("s3", region_name=REGION)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "backend"}


@app.get("/api")
def api():
    REQUEST_COUNTER.inc()
    return {"message": "Hello from FastAPI running on Amazon EKS!"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return generate_latest()


@app.get("/files")
def list_files():
    response = s3.list_objects_v2(Bucket=BUCKET)

    files = []
    for obj in response.get("Contents", []):
        files.append({
            "name": obj["Key"],
            "size": obj["Size"]
        })

    return {"bucket": BUCKET, "files": files}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()

    s3.put_object(
        Bucket=BUCKET,
        Key=file.filename,
        Body=data
    )

    return {"uploaded": file.filename}


@app.get("/download/{filename}")
def download(filename: str):
    obj = s3.get_object(Bucket=BUCKET, Key=filename)

    return StreamingResponse(
        io.BytesIO(obj["Body"].read()),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.delete("/files/{filename}")
def delete_file(filename: str):
    s3.delete_object(Bucket=BUCKET, Key=filename)
    return {"deleted": filename}

    