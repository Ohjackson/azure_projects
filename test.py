import os
from dotenv import load_dotenv
from openai import AzureOpenAI

# .env 불러오기
load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")

# Azure OpenAI 클라이언트 생성
client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=endpoint
)

# 간단한 호출 예시
response = client.chat.completions.create(
    model=deployment,
    messages=[
        {"role": "system", "content": "너는 패션 스타일 어시스턴트야."},
        {"role": "user", "content": "여름에 입기 좋은 상의 추천해줘"}
    ]
)

print(response.choices[0].message.content)
