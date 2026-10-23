# 작은 방명록

이름과 내용을 작성하고 최신 글부터 읽는 학습용 방명록입니다. FastAPI, Pydantic, Uvicorn은 Day6~Day8의 기술을 그대로 사용합니다. 화면은 HTML과 CSS이며 JavaScript, 프런트엔드 프레임워크, 추가 템플릿 라이브러리가 없습니다. SQLite는 파이썬 내장 모듈입니다.

## 실행

Python 3.13을 사용합니다. 현재 프로젝트에는 Python 3.13과 실행용 `.venv313` 환경을 준비했습니다. PowerShell에서 아래 명령으로 실행합니다.

```powershell
cd C:\AIO4\AIO4_lesson\Day1-Day8
.\.venv313\Scripts\python.exe -m uvicorn main:app --reload --port 8018
```

VS Code의 **Python: Select Interpreter**에서도 `Day1-Day8/.venv313/Scripts/python.exe`를 선택합니다. 기존 `.venv`와 저장소 루트의 환경은 그대로 보존합니다.

### 새 환경에서 설치

Python 3.13이 설치되어 있고 `py` 명령을 사용할 수 있는 컴퓨터에서는 다음과 같이 생성합니다. 이미 준비된 `.venv313`에는 다시 실행할 필요가 없습니다.

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
```

`py`가 없고 `uv`가 설치되어 있다면 `uv --no-cache venv --python 3.13 .venv313`, `uv --no-cache pip install --python .venv313/Scripts/python.exe --only-binary=:all: -r requirements.txt`를 사용합니다. `.python-version`은 uv 등에 Python 3.13을 지정하는 파일이며, 일반 `python` 명령 자체를 변경하지는 않습니다.

### pydantic-core 설치 오류

`metadata-generation-failed`, `pydantic-core`, `WinError 4551`이 함께 나오면 먼저 Python 버전을 확인합니다. 이 프로젝트의 Pydantic 2.11.5가 사용하는 pydantic-core 2.33.2에는 Windows CPython 3.13용 wheel이 있고 3.15용 wheel은 없습니다. Python 3.15에서는 소스 빌드를 시도할 수 있으며, 그 과정의 실행 파일이 Windows 애플리케이션 제어 정책에 막힐 수 있습니다. 이번 오류의 차단 파일 자체는 전체 설치 로그나 Windows 이벤트 로그 없이는 특정할 수 없습니다.

Python 3.13 환경에서 `--only-binary=:all:`로 설치하면 미리 컴파일된 wheel만 사용합니다. pip 업데이트 알림은 이 오류를 해결하라는 메시지가 아닙니다. 설치·실행 과정에서 같은 정책 오류가 계속 나면 차단된 파일을 확인해 관리자에게 문의해야 합니다.

근거: [pydantic-core 2.33.2 공식 배포 파일](https://pypi.org/project/pydantic_core/2.33.2/).

- 화면: http://127.0.0.1:8018/
- Swagger API 실습: http://127.0.0.1:8018/docs
- 종료: 터미널에서 `Ctrl+C`

기존 수업 API와 주소가 겹치지 않도록 방명록은 8018번 포트를 사용합니다.

글은 첫 실행 때 생성되는 `data/guestbook.sqlite3`에 저장됩니다. 로컬에서는 서버를 종료해도 파일이 남아 있으면 글이 유지됩니다. 경로를 바꾸려면 실행 전에 `$env:GUESTBOOK_DB_PATH = '원하는 절대경로/guestbook.sqlite3'`를 지정합니다. 원본 수업 파일은 변경하지 않습니다.

## 사용 범위와 구조

이름 1~20자, 내용 1~1,000자를 입력합니다. 앞뒤 공백을 제거하며 공백만 있는 글은 저장하지 않습니다. 목록은 최신순으로 한 페이지에 10개씩 표시합니다. 저장은 최대 1,000개로 제한하고 초과 시 기존 글을 보존한 채 등록을 거절합니다. 화면 폼 요청은 16KB까지 받습니다. 저장 한도는 호스팅의 트래픽 한도나 API 요청 전체 크기를 보장하는 제한은 아닙니다.

공개 글 작성·조회에 필요한 기능만 구현했습니다. 회원, 비밀번호, 수정·삭제, 첨부파일, 검색, 외부 API는 없습니다. 작성 성공 후 303 리다이렉트하여 브라우저 새로고침에 의한 재전송을 방지합니다.

| 파일 | 역할 |
| --- | --- |
| `main.py` | HTTP 경로, HTML 생성, 폼 처리, Swagger API |
| `models.py` | Pydantic 입력·응답 모델 |
| `database.py` | SQLite 초기화·조회·저장 |
| `templates/index.html` | 작성 폼과 목록의 HTML 틀 |
| `static/style.css` | 작은 화면에도 대응하는 CSS |
| `test_guestbook.py` | 임시 DB를 이용한 통합 테스트 |
| `ANALYSIS.md` | 수업 내용과 구현의 연결 |
| `DEPLOYMENT.md` | 무료 배포 설정과 저장소 제한 |

사용자 테이블은 `entries` 하나입니다. `id INTEGER PRIMARY KEY`, `name TEXT`, `content TEXT`, `created_at TEXT` 네 열을 사용하고 외래키·관계·별도 시퀀스 테이블은 없습니다. 작성 시간은 UTC입니다. SQL의 `?` 자리표시자로 값을 전달하고, 출력 시 `html.escape()`로 사용자 입력을 이스케이프합니다.

| 요청 | 동작 |
| --- | --- |
| `GET /?page=1` | HTML 화면 |
| `POST /entries` | HTML 폼 저장 후 `/` 이동 |
| `GET /api/entries?page=1` | JSON 목록 |
| `POST /api/entries` | JSON 작성, 성공 시 201 |
| `GET /docs` | Swagger UI |

JSON 작성 예: `{"name": "방문자", "content": "안녕하세요!"}`. 입력 오류는 422, 저장 한도 초과는 409입니다. 페이지는 1~100까지 받을 수 있습니다. 일반 화면은 JavaScript 없이 동작하고, `/docs`는 FastAPI 기본 Swagger UI를 사용합니다.

## 검증

```powershell
.\.venv313\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-dev.txt
.\.venv313\Scripts\python.exe -m pytest test_guestbook.py -q
```

`uv venv`로 만든 환경에는 pip가 없을 수 있습니다. 이 경우 설치 명령만 `uv --no-cache pip install --python .venv313/Scripts/python.exe --only-binary=:all: -r requirements-dev.txt`로 바꾸고, 테스트 명령은 그대로 사용합니다.

테스트는 임시 디렉터리의 DB만 사용합니다. 실제 글 저장·재시작 유지, 한국어·줄바꿈, HTML 이스케이프, SQL 값 전달, 입력 경계, 폼 오류, 페이지 이동, 테이블 한 개, 저장 한도를 확인합니다. 실행 결과는 `VERIFICATION.md`에 기록합니다.

무료 배포할 수 있는 서비스를 현재시점에 검색해서 표로 정리하고 각 사이트의 장단점을 분석한 후 우리가 만든 서비스를 배포하기에 가장 적합한 서비스를 추천해주고 배포방법도 최신자료를 검색해서 알려줘
