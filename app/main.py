from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import socketio                              

from app.core.config import settings
from app.db.init_db import init_db
from app.sockets import sio                   


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f" Starting {settings.APP_NAME}...")
    await init_db()
    import app.sockets.chat_socket           
    import app.sockets.call_socket            
    yield
    print(f" {settings.APP_NAME} shutting down.")


        
fastapi_app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered language learning platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
fastapi_app.add_middleware(                 
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@fastapi_app.exception_handler(Exception)    
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )


from app.api.v1.routes import auth, users, languages, sessions, chat, calls, content, progress

fastapi_app.include_router(auth.router,      prefix="/api/v1/auth",      tags=["Auth"])
fastapi_app.include_router(users.router,     prefix="/api/v1/users",     tags=["Users"])
fastapi_app.include_router(languages.router, prefix="/api/v1/languages", tags=["Languages"])
fastapi_app.include_router(sessions.router,  prefix="/api/v1/sessions",  tags=["Sessions"])
fastapi_app.include_router(chat.router,      prefix="/api/v1/chat",      tags=["Chat"])
fastapi_app.include_router(calls.router,     prefix="/api/v1/calls",     tags=["Calls"])
fastapi_app.include_router(content.router,   prefix="/api/v1/content",   tags=["Content"])
fastapi_app.include_router(progress.router,  prefix="/api/v1/progress",  tags=["Progress"])

@fastapi_app.get("/", tags=["Health"])    
async def root():
    return {"status": "running", "app": settings.APP_NAME}

@fastapi_app.get("/health", tags=["Health"]) 
async def health():
    return {"status": "healthy"}


app = socketio.ASGIApp(
    socketio_server = sio,
    other_asgi_app  = fastapi_app,
    socketio_path   = "socket.io",
)