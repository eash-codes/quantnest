"""Portfolio API — summary queries and trading commands."""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from quantnest.api.deps import (
    EventStoreDep,
    MarketDep,
    OrderEngineDep,
    PortfolioServiceDep,
    PositionRepoDep,
    TradeRepoDep,
    TransactionIdDep,
    WalletIdDep,
)
from quantnest.api.schemas import (
    CreditRequest,
    DebitRequest,
    PortfolioSummaryResponse,
    TradeRequest,
    TradeResponse,
    WalletTransactionResponse,
)
from quantnest.application.commands.portfolio_commands import BuyAssetCommand, SellAssetCommand
from quantnest.application.commands.wallet_commands import CreditWalletCommand, DebitWalletCommand
from quantnest.application.handlers import TradeCommandHandler, WalletCommandHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/health", summary="Service health check")
async def health_check() -> dict:
    return {"status": "healthy"}


@router.get(
    "/{wallet_id}/summary",
    response_model=PortfolioSummaryResponse,
    summary="Full portfolio analytics snapshot",
)
async def get_portfolio_summary(
    wallet_id: WalletIdDep,
    service: PortfolioServiceDep,
) -> PortfolioSummaryResponse:
    return PortfolioSummaryResponse(**service.get_summary(wallet_id))


@router.post(
    "/{wallet_id}/credit",
    response_model=WalletTransactionResponse,
    summary="Credit funds to a wallet",
)
async def credit_wallet(
    wallet_id: WalletIdDep,
    request: CreditRequest,
    transaction_id: TransactionIdDep,
    event_store: EventStoreDep,
) -> WalletTransactionResponse:
    handler = WalletCommandHandler(event_store=event_store)
    command = CreditWalletCommand(
        wallet_id=wallet_id,
        amount=request.amount,
        transaction_id=transaction_id,
    )
    return WalletTransactionResponse(**handler.credit(command))


@router.post(
    "/{wallet_id}/debit",
    response_model=WalletTransactionResponse,
    summary="Debit funds from a wallet",
)
async def debit_wallet(
    wallet_id: WalletIdDep,
    request: DebitRequest,
    transaction_id: TransactionIdDep,
    event_store: EventStoreDep,
) -> WalletTransactionResponse:
    handler = WalletCommandHandler(event_store=event_store)
    command = DebitWalletCommand(
        wallet_id=wallet_id,
        amount=request.amount,
        transaction_id=transaction_id,
    )
    return WalletTransactionResponse(**handler.debit(command))


@router.post(
    "/{wallet_id}/buy",
    response_model=TradeResponse,
    status_code=status.HTTP_200_OK,
    summary="Buy shares at the current market price",
)
async def buy_asset(
    wallet_id: WalletIdDep,
    request: TradeRequest,
    transaction_id: TransactionIdDep,
    engine: OrderEngineDep,
    market: MarketDep,
    event_store: EventStoreDep,
    positions: PositionRepoDep,
    trades: TradeRepoDep,
) -> TradeResponse:
    handler = TradeCommandHandler(
        engine,
        market=market,
        event_store=event_store,
        position_repository=positions,
        trade_repository=trades,
    )
    command = BuyAssetCommand(
        wallet_id=wallet_id,
        symbol=request.symbol,
        quantity=request.quantity,
        transaction_id=transaction_id,
    )
    return TradeResponse(**handler.buy(command))


@router.post(
    "/{wallet_id}/sell",
    response_model=TradeResponse,
    status_code=status.HTTP_200_OK,
    summary="Sell shares at the current market price",
)
async def sell_asset(
    wallet_id: WalletIdDep,
    request: TradeRequest,
    transaction_id: TransactionIdDep,
    engine: OrderEngineDep,
    market: MarketDep,
    event_store: EventStoreDep,
    positions: PositionRepoDep,
    trades: TradeRepoDep,
) -> TradeResponse:
    handler = TradeCommandHandler(
        engine,
        market=market,
        event_store=event_store,
        position_repository=positions,
        trade_repository=trades,
    )
    command = SellAssetCommand(
        wallet_id=wallet_id,
        symbol=request.symbol,
        quantity=request.quantity,
        transaction_id=transaction_id,
    )
    return TradeResponse(**handler.sell(command))
