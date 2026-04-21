"""Gespa OS — FastAPI entry point."""
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.seed import seed
from app.auth.routes import router as auth_router
from app.routers.workspaces import router as workspaces_router
from app.routers.leads import router as leads_router
from app.routers.agents import router as agents_router
from app.routers.whatsapp import router as whatsapp_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Başlangıçta tabloları oluştur + seed et
    print("🚀 Gespa OS başlatılıyor...")
    try:
        seed()
    except Exception as e:
        print(f"⚠ Seed hatası (devam ediliyor): {e}")
    yield
    print("👋 Gespa OS kapanıyor...")


app = FastAPI(
    title="Gespa OS",
    description="Kişisel CEO Asistanı — AI departmanları + workspace sistemi",
    version="0.2.0",
    lifespan=lifespan,
)


# CORS — lokal geliştirme için Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://os.gespaenerji.com",
        "https://aigespaenerjicom-production.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API router'ları
app.include_router(auth_router)
app.include_router(workspaces_router)
app.include_router(leads_router)
app.include_router(agents_router)
app.include_router(whatsapp_router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "gespa-os",
        "version": "0.2.0",
        "environment": settings.environment,
    }


# ─────────────────────────────────────────────────────────────
# Static frontend serve (Vite build çıktısı)
# Railway build sırasında apps/web/dist → apps/api/static kopyalanır
# ─────────────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    # Asset'ler (JS, CSS)
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA routing — React Router için tüm frontend route'ları index.html'e yönlendir."""
        # API path'lerini atla
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}

        # Dosya varsa direkt serve et (favicon.ico gibi)
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # Aksi halde SPA'ya yönlendir
        return FileResponse(STATIC_DIR / "index.html")

else:
    @app.get("/")
    def root():
        return {
            "app": "Gespa OS API",
            "status": "running",
            "note": "Frontend build bulunamadı. Lokal geliştirmede Vite dev server kullan (http://localhost:5173).",
            "docs": "/docs",
        }
