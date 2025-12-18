import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .db.session import init_db, get_engine
from .db.seed_users import seed_initial_users
from .routers import marketplaces, auth, users, history, recommendations, refresh, po

app = FastAPI(title="Estim API", version="0.2.0")

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    # Seed initial users
    engine = get_engine()
    with Session(engine) as session:
        seed_initial_users(session)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(marketplaces.router)
app.include_router(history.router)
app.include_router(recommendations.router)
app.include_router(refresh.router)
app.include_router(po.router)
