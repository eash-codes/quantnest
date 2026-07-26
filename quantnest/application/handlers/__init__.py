"""Command handlers for wallet and trading operations.

Each handler receives its collaborators by injection and returns a plain
dictionary. Business-rule violations propagate as domain exceptions, which the
API layer translates into HTTP responses.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quantnest.application.commands.portfolio_commands import BuyAssetCommand, SellAssetCommand
from quantnest.application.commands.wallet_commands import CreditWalletCommand, DebitWalletCommand
from quantnest.domain.order_engine import OrderExecutionEngine
from quantnest.domain.portfolio import Portfolio
from quantnest.domain.ports import (
    EventStore,
    MarketDataProvider,
    PositionRepository,
    TradeRepository,
)
from quantnest.domain.wallet import Wallet

logger = logging.getLogger(__name__)


class WalletCommandHandler:
    """Handles wallet credits and debits."""

    def __init__(self, event_store: Optional[EventStore] = None) -> None:
        self._event_store = event_store

    def credit(self, command: CreditWalletCommand) -> Dict[str, Any]:
        wallet = Wallet(command.wallet_id, event_store=self._event_store)
        wallet.credit(command.amount, command.transaction_id)

        logger.info(
            "Wallet credited",
            extra={
                "wallet_id": command.wallet_id,
                "amount": str(command.amount),
                "transaction_id": command.transaction_id,
            },
        )

        return {
            "wallet_id": command.wallet_id,
            "amount": float(command.amount),
            "transaction_id": command.transaction_id,
            "new_balance": float(wallet.balance),
            "message": f"Credited {command.amount} to wallet {command.wallet_id}",
        }

    def debit(self, command: DebitWalletCommand) -> Dict[str, Any]:
        wallet = Wallet(command.wallet_id, event_store=self._event_store)
        wallet.debit(command.amount, command.transaction_id)

        logger.info(
            "Wallet debited",
            extra={
                "wallet_id": command.wallet_id,
                "amount": str(command.amount),
                "transaction_id": command.transaction_id,
            },
        )

        return {
            "wallet_id": command.wallet_id,
            "amount": float(command.amount),
            "transaction_id": command.transaction_id,
            "new_balance": float(wallet.balance),
            "message": f"Debited {command.amount} from wallet {command.wallet_id}",
        }


class TradeCommandHandler:
    """Handles buy and sell commands through the order execution engine."""

    def __init__(
        self,
        engine: OrderExecutionEngine,
        *,
        market: Optional[MarketDataProvider] = None,
        event_store: Optional[EventStore] = None,
        position_repository: Optional[PositionRepository] = None,
        trade_repository: Optional[TradeRepository] = None,
    ) -> None:
        self._engine = engine
        self._market = market
        self._event_store = event_store
        self._position_repository = position_repository
        self._trade_repository = trade_repository

    def buy(self, command: BuyAssetCommand) -> Dict[str, Any]:
        return self._execute(command, "BUY")

    def sell(self, command: SellAssetCommand) -> Dict[str, Any]:
        return self._execute(command, "SELL")

    def _execute(self, command, side: str) -> Dict[str, Any]:
        order = self._engine.place_order(
            wallet_id=command.wallet_id,
            symbol=command.symbol,
            side=side,
            quantity=command.quantity,
            order_type="MARKET",
            transaction_id=command.transaction_id,
        )

        response: Dict[str, Any] = {
            "wallet_id": command.wallet_id,
            "symbol": command.symbol,
            "quantity": float(command.quantity),
            "transaction_id": command.transaction_id,
            "order_id": order.order_id,
            "order_status": order.status,
        }

        if order.is_rejected:
            response["success"] = False
            response["message"] = order.rejection_reason or "The order was rejected."
            return response

        verb = "Bought" if side == "BUY" else "Sold"
        response["success"] = True
        response["message"] = f"{verb} {command.quantity} {command.symbol}"

        portfolio = Portfolio(
            command.wallet_id,
            self._market,
            event_store=self._event_store,
            position_repository=self._position_repository,
            trade_repository=self._trade_repository,
        )
        response["portfolio_summary"] = {
            "cash": float(portfolio.cash()),
            "total_value": float(portfolio.total_value()),
            "positions": {
                symbol: float(quantity) for symbol, quantity in portfolio.positions.items()
            },
        }

        return response


__all__ = ["WalletCommandHandler", "TradeCommandHandler"]
