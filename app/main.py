from contextlib import asynccontextmanager
from fastapi import FastAPI ,Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.init_db import init_db




@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f" Starting {settings.APP_NAME}...")
    await init_db()          
    yield
   
    print(f" {settings.APP_NAME} shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered language learning platform",
    version="1.0.0",
    docs_url="/docs",       
    redoc_url="/redoc",     
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )

#  Routes
from app.api.v1.routes import auth ,users, languages
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(languages.router, prefix="/api/v1/languages", tags=["Languages"])



@app.get("/", tags=["Health"])
async def root():
    return {"status": "running", "app": settings.APP_NAME}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}