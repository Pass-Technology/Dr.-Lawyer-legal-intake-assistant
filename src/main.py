from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool
import os

load_dotenv(".env")

from routes import base, start_intake, optimize, optimize_offer, optimize_case_description, upload_parser

# Setup the connection pool settings
DB_URL = os.getenv("DATABASE_URL")
if DB_URL and "sslmode" not in DB_URL:
    DB_URL += "?sslmode=require"

connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

# Define the Lifespan (Startup/Shutdown logic)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the pool object
    pool = AsyncConnectionPool(
        conninfo=DB_URL,
        max_size=10,
        kwargs=connection_kwargs,
        open=False, # Add this to tell it NOT to open in the constructor
    )
    
    # Explicitly open the pool (This is what the warning wants)
    await pool.open()
    
    # Create the saver object
    saver = AsyncPostgresSaver(pool)
    
    # Run setup
    await saver.setup()
    
    # Store in state
    app.state.checkpointer = saver
    app.state.db_pool = pool
    
    yield
    
    # Close the pool on shutdown
    await pool.close()

# Pass lifespan to FastAPI
app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:3000",       # React dev server (common)
    "http://localhost:5173",       # Vite dev server (very common 2025–2026)
    "http://localhost:4200",       # Angular dev
    "http://127.0.0.1:3000",       # sometimes people use 127 instead of localhost
    #"https://your-frontend-domain.com",          # ← production frontend
    #"https://staging.your-app.com",              # if you have staging
    # "https://*.your-vercel-domain.app",        # if needed (better with regex below)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],              # ← or ["*"] for dev only (see warning below)
    allow_credentials=True,             # ← set True if using cookies / Authorization header
    allow_methods=["*"],                # allows GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_headers=["*"],                # allows Content-Type, Authorization, etc.
)

app.include_router(start_intake.start_intake_router)
app.include_router(upload_parser.upload_router)
app.include_router(optimize_case_description.refine_router)
app.include_router(optimize.optimize_router)
app.include_router(optimize_offer.offer_router)
app.include_router(base.base_router)