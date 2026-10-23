"""실행: python -m uvicorn main:app --reload (현재 폴더: Day1-Day8)."""

import asyncio
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import ValidationError

import database
from models import EntryCreate, EntryOut

BASE_DIR = Path(__file__).resolve().parent
PAGE_TEMPLATE = Template((BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8"))
MAX_FORM_BYTES = 16 * 1024
MAX_PAGES = (database.MAX_ENTRIES + database.PAGE_SIZE - 1) // database.PAGE_SIZE


@asynccontextmanager
async def lifespan(app):
    await asyncio.to_thread(database.init_db)
    yield


app = FastAPI(title="작은 방명록", version="1.0.0", lifespan=lifespan)


def render_page(page=1, error="", name="", content="", status_code=200):
    records = database.list_entries(page)
    total = database.count_entries()
    cards = []
    for record in records:
        cards.append(
            '<article class="entry">'
            f'<header><strong>{escape(record["name"])}</strong>'
            f'<time datetime="{escape(record["created_at"])}">'
            f'{escape(record["created_at"].replace("T", " ").replace("Z", " UTC"))}'
            '</time></header>'
            f'<p>{escape(record["content"])}</p></article>'
        )
    navigation = []
    if page > 1:
        navigation.append(f'<a href="/?page={page - 1}">← 이전</a>')
    navigation.append(f'<span>{page} 페이지</span>')
    if page * database.PAGE_SIZE < total:
        navigation.append(f'<a href="/?page={page + 1}">다음 →</a>')
    html = PAGE_TEMPLATE.substitute(
        error=f'<p class="error" role="alert">{escape(error)}</p>' if error else "",
        name=escape(name, quote=True),
        content=escape(content),
        entries="".join(cards) or '<p class="empty">아직 남겨진 글이 없어요. 첫 인사를 남겨 주세요.</p>',
        total=total,
        navigation=" ".join(navigation),
    )
    return HTMLResponse(html, status_code=status_code)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(page: int = Query(default=1, ge=1, le=MAX_PAGES)):
    return render_page(page)


@app.get("/style.css", include_in_schema=False)
def stylesheet():
    return FileResponse(BASE_DIR / "static" / "style.css", media_type="text/css")


def save_form(values):
    try:
        entry = EntryCreate.model_validate(values)
    except ValidationError:
        return render_page(
            error="이름은 1~20자, 내용은 1~1,000자로 입력해 주세요. 공백만 입력할 수 없습니다.",
            name=values.get("name", ""),
            content=values.get("content", ""),
            status_code=422,
        )
    try:
        database.add_entry(entry)
    except ValueError as error:
        return render_page(error=str(error), name=entry.name, content=entry.content, status_code=409)
    # 새로고침으로 같은 글이 다시 등록되지 않도록 GET으로 이동한다.
    return RedirectResponse(url="/", status_code=303)


@app.post("/entries", response_class=HTMLResponse, include_in_schema=False)
async def submit_entry(request: Request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/x-www-form-urlencoded":
        raise HTTPException(status_code=415, detail="HTML 폼 형식으로 전송해 주세요.")
    # 표준 HTML 폼은 urllib로 읽어 python-multipart 추가 설치를 피한다.
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_FORM_BYTES:
            raise HTTPException(status_code=413, detail="요청은 16KB를 넘을 수 없습니다.")
        body.extend(chunk)
    try:
        fields = parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=2, errors="strict")
    except (UnicodeDecodeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="올바른 폼 데이터가 아닙니다.") from error
    if any(len(values) != 1 for values in fields.values()):
        raise HTTPException(status_code=400, detail="같은 항목을 여러 번 보낼 수 없습니다.")
    values = {key: items[0] for key, items in fields.items()}
    return await asyncio.to_thread(save_form, values)


@app.get("/api/entries", response_model=list[EntryOut], summary="방명록 목록 (페이지당 10개)")
def read_entries(page: int = Query(default=1, ge=1, le=MAX_PAGES)):
    return database.list_entries(page)


@app.post("/api/entries", response_model=EntryOut, status_code=201, summary="방명록 작성")
def create_entry(entry: EntryCreate):
    try:
        return database.add_entry(entry)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
