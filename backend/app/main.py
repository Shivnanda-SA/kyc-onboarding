from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import cases
from .storage import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def create_app() -> FastAPI:
    app = FastAPI(title="AI KYC Onboarding POC", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173","https://kyc-onboarding-e6om.vercel.app"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz():
        from .extraction.pipeline import TESSERACT_AVAILABLE
        return {
            "ok": True,
            "tesseract_available": TESSERACT_AVAILABLE,
            "note": "Tesseract OCR is optional. Without it, image/scanned-PDF processing will return empty text.",
        }

    @app.on_event("startup")
    def _startup():
        init_db()

    app.include_router(cases.router, prefix="/api")
    return app


app = create_app()

