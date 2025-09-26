# Azure Project – Fashion Stylist Demo

이 저장소는 FastAPI와 Azure OpenAI를 연결해 패션 추천을 생성하고, 스키마 기반 HTML UI를 함께 제공합니다.

## 필수 조건
- Python 3.10+
- Azure OpenAI 리소스 (엔드포인트, API 키, 배포 모델)

## 환경 변수 설정
`.env` 파일을 루트에 생성하고 다음 값을 채웁니다.

```
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=<your-chat-deployment>
# 또는 AZURE_OPENAI_DEPLOYMENT 로 명시 가능
```

> ℹ️ `AZURE_OPENAI_ENDPOINT`에는 기본 엔드포인트(`https://...cognitiveservices.azure.com/`)를 넣거나, 전체 REST 경로(`https://.../openai/deployments/.../chat/completions?api-version=...`)를 그대로 넣어도 됩니다. 앱이 자동으로 배포 이름과 API 버전을 추출합니다.


## 로컬 실행
1. 가상환경 생성 및 패키지 설치
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. FastAPI 서버 실행
   ```bash
   uvicorn main:app --reload
   ```
3. 브라우저에서 [http://localhost:8000](http://localhost:8000) 접속 후 UI에서 요청을 전송합니다.

### 유용한 엔드포인트
- `GET /` : HTML UI 제공
- `GET /schemas` : 입력/출력 스키마 원문
- `POST /chat` : JSON 요청 → Azure OpenAI 응답
- `GET /health` : 상태 확인

## Docker로 실행
1. 이미지 빌드
   ```bash
   docker build -t azure-fashion .
   ```
2. 컨테이너 실행 (호스트의 `.env` 파일 공유)
   ```bash
   docker run --rm -p 8080:80 --env-file .env azure-fashion
   ```
3. 브라우저에서 `http://localhost:8080`에 접속합니다.

컨테이너는 Supervisor가 `gunicorn`(Uvicorn 워커)과 Nginx를 함께 실행하며, Nginx가 정적 자산을 서빙하고 애플리케이션으로 프록시합니다.

## 문제 해결
- 401 Unauthorized: API 키, 엔드포인트, API 버전, 배포 이름이 정확한지 확인하고, Docker 실행 시 `--env-file`로 전달했는지 검증합니다.
- 404 /favicon.ico: 기본 파비콘이 없어서 나는 로그이므로 무시하거나 `static/favicon.ico`를 추가합니다.
- Azure 요청 실패: `uvicorn` 로그에 표시된 오류 메시지를 그대로 UI에서 보여 주므로, 필요한 경우 Azure Portal에서 동일 자격으로 호출 테스트를 진행하세요.

## 테스트 호출 예시
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d @input_structure.txt
```

응답은 `output_structure copy.txt`에 정의된 스키마 형태의 JSON입니다. Docker 사용 시 호스트 포트를 변경했다면 URL의 포트만 맞춰 주세요.
