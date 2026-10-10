import io
import os

# Configure a test environment before importing the application.
os.environ.setdefault("AWS_REGION", "ap-south-1")
os.environ.setdefault("S3_BUCKET", "unit-test-bucket")
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

from fastapi.testclient import TestClient
from app.main import app, s3

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "backend",
    }


def test_api_endpoint():
    response = client.get("/api")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Hello from FastAPI running on Amazon EKS!"
    }


def test_metrics_endpoint():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_list_files(monkeypatch):
    monkeypatch.setattr(
        s3,
        "list_objects_v2",
        lambda **kwargs: {
            "Contents": [
                {"Key": "report.txt", "Size": 123},
                {"Key": "data.csv", "Size": 456},
            ]
        },
    )

    response = client.get("/files")

    assert response.status_code == 200
    assert response.json() == {
        "bucket": "unit-test-bucket",
        "files": [
            {"name": "report.txt", "size": 123},
            {"name": "data.csv", "size": 456},
        ],
    }


def test_list_files_when_bucket_is_empty(monkeypatch):
    monkeypatch.setattr(s3, "list_objects_v2", lambda **kwargs: {})

    response = client.get("/files")

    assert response.status_code == 200
    assert response.json()["files"] == []


def test_upload_file(monkeypatch):
    calls = {}

    def fake_put_object(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(s3, "put_object", fake_put_object)

    response = client.post(
        "/upload",
        files={"file": ("hello.txt", b"Hello from unit tests", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json() == {"uploaded": "hello.txt"}
    assert calls["Bucket"] == "unit-test-bucket"
    assert calls["Key"] == "hello.txt"
    assert calls["Body"] == b"Hello from unit tests"


def test_download_file(monkeypatch):
    monkeypatch.setattr(
        s3,
        "get_object",
        lambda **kwargs: {
            "Body": io.BytesIO(b"download test content")
        },
    )

    response = client.get("/download/hello.txt")

    assert response.status_code == 200
    assert response.content == b"download test content"
    assert "attachment" in response.headers["content-disposition"]


def test_delete_file(monkeypatch):
    calls = {}

    def fake_delete_object(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(s3, "delete_object", fake_delete_object)

    response = client.delete("/files/hello.txt")

    assert response.status_code == 200
    assert response.json() == {"deleted": "hello.txt"}
    assert calls["Bucket"] == "unit-test-bucket"
    assert calls["Key"] == "hello.txt"


def test_upload_requires_file():
    response = client.post("/upload")

    assert response.status_code == 422
