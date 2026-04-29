from fastapi import FastAPI
from contextlib import asynccontextmanager
from utils.patching import apply_patches
from routes import client_router, proxy_router, base_router, ui_router
import db

apply_patches()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    yield
    await db.close_pool()

app = FastAPI(title="NeMo Data Designer SaaS API", lifespan=lifespan)

app.include_router(client_router.router)
app.include_router(proxy_router.router)
app.include_router(base_router.router)
app.include_router(ui_router.router)
