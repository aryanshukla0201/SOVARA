from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Multimodal AI Workbench MVP")
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
