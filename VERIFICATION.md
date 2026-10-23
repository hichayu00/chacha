# 검증 기록

검증일: 2026-10-23. Windows, Python 3.13.16에서 확인했습니다.

## 설치 오류 복구 후 재검증

사용자가 보고한 `pydantic-core`의 `metadata-generation-failed`와 `WinError 4551`을 확인했습니다. 당시 `Day1-Day8/.venv/pyvenv.cfg`는 Python 3.15.0을 참조했습니다. 고정된 pydantic-core 2.33.2의 Windows CPython 3.15용 wheel이 없어 소스 빌드가 시도된 것으로 추정합니다. 실제 정책에 차단된 실행 파일은 제공된 로그만으로 특정할 수 없습니다.

기존 `.venv`는 보존하고 실행 가능한 Python 3.13.16으로 `.venv313`을 생성했습니다. 다음 명령으로 모든 패키지를 wheel로만 설치했습니다.

```powershell
.\.venv313\Scripts\python.exe -m pip install --no-cache-dir --only-binary=:all: -r requirements-dev.txt
.\.venv313\Scripts\python.exe -m pytest test_guestbook.py -q
.\.venv313\Scripts\python.exe -m pip check
```

`pydantic_core-2.33.2-cp313-cp313-win_amd64.whl` 설치 성공, **18 passed, 1 warning**, `No broken requirements found.`를 확인했습니다. Windows 보안 정책은 변경하지 않았습니다. README의 기본 실행·검증 경로를 `.venv313`으로 바꾸고 일반 `python`으로 가상환경을 다시 만드는 안내를 명시적인 Python 3.13 선택으로 수정했습니다.

실제 HTTP 확인 시 `127.0.0.1:8000`은 기존 인사 API를 반환했습니다. 해당 서비스를 종료하지 않고 방명록을 `127.0.0.1:8018`에서 실행하여 `GET /`의 HTML 200 응답과 OpenAPI의 방명록 제목·경로를 확인했습니다. 사용자 접속을 위해 복구한 서버는 실행 상태로 두었습니다. 아래는 최초 구현 당시의 검증 기록입니다.

## 환경

저장소 루트의 기존 `.venv`는 존재하지 않는 Python 3.15 실행 경로를 참조해 실행할 수 없었습니다. 기존 환경을 변경하지 않고 `Day1-Day8/.python`, `Day1-Day8/.venv`, `Day1-Day8/.uv-cache`에 검증 환경을 준비했습니다. 재현하려면 설치된 `uv`로 README의 대체 설치 명령을 사용할 수 있습니다.

직접 의존성은 수업과 같은 FastAPI 0.115.12, Pydantic 2.11.5, Uvicorn 0.34.2입니다. 테스트에는 httpx 0.28.1, pytest 8.3.5를 사용했습니다. 실제 런타임·캐시·데이터 파일은 `.gitignore`로 제외했습니다.

## 자동 테스트

실행 위치: `Day1-Day8`

```powershell
.\.venv\Scripts\python.exe -m pytest test_guestbook.py -q
```

결과: **18 passed**, 경고 1개. 경고는 수업 버전 Starlette의 TestClient가 최신 AnyIO의 폐기 예정 별칭을 참조한다는 `DeprecationWarning`입니다. 동작 실패는 없었습니다. 수업 패키지를 임의 업그레이드하지 않았습니다.

확인한 동작:

- 빈 목록, 폼 구조, CSS 응답, HTML 틀의 값 치환
- HTML 폼의 303 이동, 한국어·특수문자·줄바꿈, 앞뒤 공백 제거
- 앱 수명주기 재시작 후 같은 SQLite 파일의 글 유지
- 필수 값, 공백, 이름·본문 길이, 자료형, 추가 필드 거부
- 길이 상한 정상 입력, Swagger 스키마와 문서 응답
- HTML 태그 이스케이프, SQL처럼 보이는 입력을 일반 문자열로 저장
- SQLite 사용자 테이블이 `entries` 한 개뿐임
- 오류 시 작성값의 안전한 재표시
- 잘못된 전송 형식, 중복 필드, UTF-8 오류, 16KB 초과 폼 거부
- 최신순·10개 페이지 나누기·잘못된 페이지 거부
- 저장 한도 초과 시 409 및 기존 글 유지

## 실제 서버 확인

별도 `.preview/guestbook.sqlite3`를 지정하고 Uvicorn을 127.0.0.1:8018에서 실행했습니다. httpx로 실제 TCP HTTP 요청을 보내 아래를 확인했습니다. 검증 서버는 확인 후 종료했습니다. 실제 앱의 기본 데이터 파일에 샘플 글을 넣지 않았습니다.

```text
LIVE HTTP: home=200, form=303, persisted list=200, CSS=200, docs=200, schema=200
Initial HTML bytes: 1688
```

파이썬 소스 컴파일 검사와 `uv --no-cache pip check --python .venv/Scripts/python.exe`도 통과했습니다. 의존성 검사는 20개 패키지가 호환됨을 확인했습니다. 일반 캐시 경로 접근 제한이 있어 검사 시 캐시를 사용하지 않았습니다.

## 확인하지 않은 범위

현재 브라우저 도구에 연결된 브라우저가 없어 실제 화면 캡처와 시각적 배치 검사는 수행하지 못했습니다. HTML 응답과 폼 처리는 자동 테스트 및 실제 HTTP 요청으로 확인했습니다. 모바일용 CSS는 작성했으나 기기별 시각 검증은 하지 않았습니다.

외부 호스팅에 게시하지 않았으며 Render에서의 실제 빌드·과금·장기 운영은 검증하지 않았습니다. 무료 호스팅의 SQLite 파일 소실과 사용량 제한은 공식 문서로 확인하고 `DEPLOYMENT.md`에 기록했습니다. 로컬 파일의 재시작 후 유지가 호스팅의 영구 보존을 의미하지는 않습니다.
