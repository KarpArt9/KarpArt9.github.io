import asyncio
import logging
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.bot.run import launch_task
from app.config import BASE_DIR, settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, leads, products, stats, uploads
from app.seed import seed_if_empty

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await seed_if_empty(session)

    bot_task = launch_task()
    try:
        yield
    finally:
        if bot_task:
            bot_task.cancel()
            await asyncio.gather(bot_task, return_exceptions=True)
        await engine.dispose()


app = FastAPI(title="Райский холод", lifespan=lifespan)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(uploads.router, prefix="/api", tags=["uploads"])

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")
app.mount("/admin", StaticFiles(directory=str(BASE_DIR / "admin"), html=True), name="admin")

IMAGES_DIR = BASE_DIR / "images"

PLACEHOLDER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
    <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#0a6650"/>
            <stop offset="100%" stop-color="#064e3b"/>
        </linearGradient>
    </defs>
    <rect width="400" height="300" fill="url(#g)"/>
    <circle cx="335" cy="35" r="70" fill="#10b981" opacity="0.18"/>
    <circle cx="30" cy="270" r="50" fill="#f0c419" opacity="0.12"/>
    <g transform="translate(200,120)" fill="#34d399" opacity="0.9">
        <path d="M0 -34 L6 -14 L26 -14 L9 -2 L15 18 L0 6 L-15 18 L-9 -2 L-26 -14 L-6 -14 Z"/>
    </g>
    <text x="200" y="200" font-family="Segoe UI, Arial, sans-serif" font-size="26" font-weight="700" fill="#ffffff" text-anchor="middle">{label}</text>
    <text x="200" y="228" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#a7f3d0" text-anchor="middle">Райский холод</text>
</svg>"""


@app.get("/images/{brand}/{image_file}", include_in_schema=False)
async def product_image(brand: str, image_file: str):
    path = IMAGES_DIR / Path(brand).name / Path(image_file).name
    if path.is_file():
        return FileResponse(path)
    return Response(
        PLACEHOLDER_SVG.format(label=escape(Path(image_file).stem[:30])),
        media_type="image/svg+xml",
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#059669"/>'
        '<text x="32" y="44" font-size="36" text-anchor="middle">\u2744\ufe0f</text></svg>'
    )
    return Response(svg, media_type="image/svg+xml")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(BASE_DIR / "index.html")
