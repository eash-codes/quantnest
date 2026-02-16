"""QuantNest Day 6A FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .portfolio import router as portfolio_router

app = FastAPI(title="QuantNest Ledger API", version="6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_router)

@app.get("/")
async def root():
    return {"message": "QuantNest Day 6A - Production Ledger API"}
