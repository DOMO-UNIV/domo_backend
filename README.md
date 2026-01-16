
# 🌊 Domo Collaboration Platform - Backend

전주대학교 팀 프로젝트 협업을 위한 FastAPI 기반 백엔드 서버입니다.

**FastAPI + PostgreSQL + Weaviate(VectorWave)** 환경으로 구성되어 있습니다.

## 🛠️ 사전 준비 (Prerequisites)

이 프로젝트는 **Docker** 환경에서 실행하는 것을 권장합니다.

* [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치 및 실행

## 🚀 시작하기 (Getting Started)

### 1. 환경 변수 설정

프로젝트 루트 폴더에 `.env` 파일을 생성하고 아래 내용을 입력합니다. (OpenAI 키는 필수가 아닙니다)

```env
OPENAI_API_KEY=your_openai_api_key_here

```

### 2. 서버 실행

터미널에서 아래 명령어를 입력하여 컨테이너를 빌드하고 실행합니다.

```bash
docker-compose up --build

```

> **참고:** 처음 실행 시 Weaviate(벡터 DB)가 준비될 때까지 백엔드 로그에 `⏳ [VectorWave] DB not ready...` 메시지가 뜰 수 있습니다. 잠시 기다리면 자동으로 연결됩니다.

### 3. 접속 확인

서버가 정상적으로 실행되면 아래 주소로 접속 가능합니다.

* **API 서버:** [http://localhost:8000](https://www.google.com/search?q=http://localhost:8000)
* **자동 생성된 API 문서 (Swagger UI):** [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs) ✅ **여기서 모든 API 테스트 가능**

## 🔐 인증 방식 (Authentication)

이 서버는 **세션 기반 쿠키(HttpOnly Cookie)** 인증을 사용합니다.

1. `/api/auth/signup`으로 계정 생성
2. `/api/auth/login`으로 로그인 성공 시, 브라우저/Postman에 세션 쿠키가 자동 저장됩니다.
3. 이후 다른 API 호출 시 별도의 토큰 없이도 쿠키를 통해 인증이 유지됩니다.

## 📂 주요 기능 레이아웃

* **Auth:** 회원가입, 로그인, 로그아웃, 내 정보 조회
* **Workspace:** 팀 생성, 프로젝트 관리, 팀원 초대(`email` 기반)
* **Kanban Board:** 컬럼 생성, 카드(포스트잇) 생성 및 드래그 앤 드롭 이동
* **Schedule:** 개인 시간표 등록 및 팀원 간 **공통 비어있는 시간 계산**

---

### 💡 프론트엔드 테스트 팁

* **Postman 사용 시:** 로그인을 한 번 성공하면 쿠키가 자동으로 세팅되어 다른 API를 바로 호출할 수 있습니다.
* **CORS 설정:** 현재 로컬 개발 환경에 맞춰 기본 설정되어 있습니다.

---
