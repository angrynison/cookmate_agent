# 웹 프레임 워크 FastApi, 서버 구동엔진 uvicorn -> spring boot, tomcat
from fastapi import FastAPI
import uvicorn

# 애플리케이션 객체 생성
app = FastAPI(
    title="Recipe AI Agent API",
    description="개인 식재료 기반으로 레시피를 추천하는 Langraph AI Agent 입니다",
    version="1.0.0"
)

# 헬스 체크(Health Check) 엔드포인트
@app.get("/")
async def health_check():
    return {
        "status": "UP",
        "service": "fastapi-ai-agent"
    }

# 서버 실행 
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)



