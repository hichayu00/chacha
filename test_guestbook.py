"""임시 SQLite 파일을 사용하는 통합 테스트. 실제 방명록 데이터는 건드리지 않는다."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

import database
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "guestbook.sqlite3")
    with TestClient(app) as test_client:
        yield test_client


def test_home_and_assets(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'lang="ko"' in response.text
    assert '<form action="/entries" method="post"' in response.text
    assert "아직 남겨진 글이 없어요" in response.text
    assert "<script" not in response.text
    assert "$entries" not in response.text
    assert client.get("/style.css").status_code == 200


def test_form_redirect_unicode_and_persistence(client):
    response = client.post(
        "/entries", data={"name": "  방문자  ", "content": "안녕하세요!\n반갑습니다. & + %"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "방문자" in client.get("/").text
    # 앱의 수명주기를 다시 시작해도 같은 DB 파일을 읽는다.
    with TestClient(app) as restarted:
        entries = restarted.get("/api/entries").json()
        assert len(entries) == 1
        assert entries[0]["name"] == "방문자"
        assert entries[0]["content"] == "안녕하세요!\n반갑습니다. & + %"
        assert entries[0]["created_at"].endswith("Z")


@pytest.mark.parametrize("payload", [
    {}, {"name": "가"}, {"name": "", "content": "인사"},
    {"name": " \t ", "content": "인사"}, {"name": "가" * 21, "content": "인사"},
    {"name": "방문자", "content": "\n \t"}, {"name": "방문자", "content": "가" * 1001},
    {"name": "방문자", "content": "인사", "admin": True},
    {"name": 123, "content": "인사"}, {"name": None, "content": "인사"},
])
def test_api_rejects_invalid_input(client, payload):
    assert client.post("/api/entries", json=payload).status_code == 422
    assert client.get("/api/entries").json() == []


def test_length_boundaries_and_json_schema(client):
    response = client.post("/api/entries", json={"name": "가" * 20, "content": "나" * 1000})
    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert len(response.json()["content"]) == 1000
    schema = client.get("/openapi.json").json()
    fields = schema["components"]["schemas"]["EntryCreate"]
    assert fields["additionalProperties"] is False
    assert fields["properties"]["content"]["maxLength"] == 1000
    assert client.get("/docs").status_code == 200


def test_html_escaping_and_sql_parameters(client):
    name = "'); DROP TABLE entries;"[:20]
    content = '<script>alert("x")</script> & </textarea><img src=x onerror=alert(1)>'
    assert client.post("/api/entries", json={"name": name, "content": content}).status_code == 201
    html = client.get("/").text
    assert "<script>" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;" in html
    assert client.get("/api/entries").json()[0]["content"] == content
    with sqlite3.connect(database.DB_PATH) as connection:
        tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert tables == [("entries",)]


def test_form_error_preserves_escaped_values(client):
    response = client.post("/entries", data={"name": '\"><img src=x>', "content": " "})
    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert "&lt;img src=x&gt;" in response.text
    assert "<img src=x>" not in response.text
    assert client.get("/api/entries").json() == []


def test_form_transport_errors(client):
    assert client.post("/entries", json={"name": "가", "content": "나"}).status_code == 415
    headers = {"content-type": "application/x-www-form-urlencoded"}
    for body in (b"name=a&name=b", b"name=a&content=b&extra=c", b"name=%FF&content=b", b"\xff"):
        assert client.post("/entries", content=body, headers=headers).status_code == 400
    assert client.post("/entries", content=b"a" * 16385, headers=headers).status_code == 413


def test_pagination_and_newest_first(client):
    for number in range(12):
        assert client.post("/api/entries", json={"name": "방문자", "content": str(number)}).status_code == 201
    first_page = client.get("/api/entries").json()
    second_page = client.get("/api/entries?page=2").json()
    assert [entry["content"] for entry in first_page] == [str(number) for number in range(11, 1, -1)]
    assert [entry["content"] for entry in second_page] == ["1", "0"]
    assert '/?page=2' in client.get("/").text
    assert '/?page=1' in client.get("/?page=2").text
    assert client.get("/api/entries?page=3").json() == []
    for page in ("0", "-1", "abc", "101", "9" * 100):
        assert client.get(f"/api/entries?page={page}").status_code == 422
        assert client.get(f"/?page={page}").status_code == 422


def test_storage_limit(client, monkeypatch):
    monkeypatch.setattr(database, "MAX_ENTRIES", 2)
    payload = {"name": "방문자", "content": "안녕하세요"}
    assert client.post("/api/entries", json=payload).status_code == 201
    assert client.post("/entries", data=payload, follow_redirects=False).status_code == 303
    assert client.post("/api/entries", json=payload).status_code == 409
    response = client.post("/entries", data=payload)
    assert response.status_code == 409
    assert "방명록이 가득 찼습니다" in response.text
    assert len(client.get("/api/entries").json()) == 2
