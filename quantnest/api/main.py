"""QuantNest Day 9 FastAPI - History & Observability."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .portfolio import router as portfolio_router
from .history import router as history_router
from .orders import router as orders_router
from .market import router as market_router

app = FastAPI(title="QuantNest Trading Platform", version="10.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_router)
app.include_router(history_router)
app.include_router(orders_router)
app.include_router(market_router)

@app.get("/")
async def root():
    return {"message": "QuantNest Day 9 - Trading Platform with History & Observability"}
