"""FastAPI 앱: Azure OpenAI 기반 패션 추천 API 및 웹 UI."""

import json
import os
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from openai import AzureOpenAI
from pydantic import BaseModel, Field

# .env 파일로부터 환경 변수 로드
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INPUT_SCHEMA_PATH = BASE_DIR / "input_structure.txt"
OUTPUT_SCHEMA_PATH = BASE_DIR / "output_structure copy.txt"

INPUT_SCHEMA_TEXT = INPUT_SCHEMA_PATH.read_text(encoding="utf-8") if INPUT_SCHEMA_PATH.exists() else ""
OUTPUT_SCHEMA_TEXT = OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8") if OUTPUT_SCHEMA_PATH.exists() else ""


def _resolve_azure_settings() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """환경 변수 또는 전체 REST URL에서 Azure 설정을 도출한다."""
    endpoint_env = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version_env = os.getenv("AZURE_OPENAI_API_VERSION")
    deployment_env = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not endpoint_env:
        return None, api_version_env, deployment_env

    parsed = urlparse(endpoint_env)
    base_endpoint = endpoint_env

    if parsed.path and "/openai/" in parsed.path:
        # 사용자가 전체 REST 경로를 제공한 경우, 기본 엔드포인트/배포/API 버전을 추출한다.
        openai_root = parsed.path.split("/openai", 1)[0]
        base_endpoint = f"{parsed.scheme}://{parsed.netloc}{openai_root}".rstrip("/")

        segments = [segment for segment in parsed.path.split('/') if segment]
        if "deployments" in segments:
            idx = segments.index("deployments")
            if idx + 1 < len(segments) and not deployment_env:
                deployment_env = segments[idx + 1]

        query = parse_qs(parsed.query)
        if not api_version_env and "api-version" in query:
            api_version_env = query["api-version"][0]

    return base_endpoint, api_version_env, deployment_env


AZURE_ENDPOINT, AZURE_API_VERSION, AZURE_DEPLOYMENT = _resolve_azure_settings()
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
if not AZURE_API_VERSION:
    AZURE_API_VERSION = "2024-08-01-preview"

client: Optional[AzureOpenAI] = None
if AZURE_ENDPOINT and AZURE_API_KEY:
    client = AzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION,
    )

SYSTEM_PROMPT = (
    "You are a fashion stylist assistant. Always respond with valid JSON that strictly follows this schema:\n"
    f"{OUTPUT_SCHEMA_TEXT}\n\n"
    "Guidelines:\n"
    "- Ensure every response can be parsed as JSON without extra commentary.\n"
    "- Echo the user profile values into `profile_echo`.\n"
    "- Produce exactly `options.need_count` outfit recommendations when feasible.\n"
    "- Populate perfumes that match each outfit; leave arrays empty when unsure.\n"
    "- Use `null` for unknown scalar values instead of placeholders.\n"
    "- Provide concise Korean copy where appropriate.\n"
)

# FastAPI 앱 초기화
app = FastAPI(title="Azure Fashion Stylist")


class Occupation(BaseModel):
    industry: str
    role: str


class UserProfile(BaseModel):
    gender: str
    age: int
    occupation: Occupation
    style_preference: List[str] = Field(default_factory=list)


class Options(BaseModel):
    season: Optional[str] = None
    budget: Optional[str] = None
    need_count: int = Field(gt=0, le=5)


class ChatRequest(BaseModel):
    user_profile: UserProfile
    options: Options


@app.get("/")
async def serve_ui() -> FileResponse:
    """정적 HTML UI 제공."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="UI 파일을 찾을 수 없습니다.")
    return FileResponse(index_path)


@app.get("/schemas")
async def get_schemas():
    """프론트엔드 참고용 입력/출력 스키마 제공."""
    return {
        "input": INPUT_SCHEMA_TEXT,
        "output": OUTPUT_SCHEMA_TEXT,
    }


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Azure OpenAI와 연동하여 패션 추천 생성."""
    if client is None or not AZURE_DEPLOYMENT:
        raise HTTPException(status_code=500, detail="Azure OpenAI 설정이 누락되었습니다. 환경 변수를 확인하세요.")

    payload = request.model_dump()
    user_json = json.dumps(payload, ensure_ascii=False, indent=2)
    user_prompt = (
        "다음 JSON 입력을 기반으로 패션 코디와 향수를 추천하세요. "
        "반드시 위에서 정의한 출력 스키마에 맞는 유효한 JSON만 반환해야 합니다.\n\n"
        f"{user_json}"
    )

    try:
        completion = client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:  # pragma: no cover - 네트워크 의존 오류 처리
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    content = completion.choices[0].message.content

    try:
        parsed_content = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f'Azure 응답 JSON 파싱 실패: {exc}') from exc

    return {"response": content, "parsed": parsed_content, "request": payload}


@app.get("/health")
async def health_check():
    """간단한 상태 체크."""
    return {"status": "ok"}
