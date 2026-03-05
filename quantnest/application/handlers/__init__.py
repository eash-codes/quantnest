"""Command handlers for wallet operations."""

from decimal import Decimal
from typing import Dict, Any
from quantnest.domain.wallet import Wallet
from quantnest.domain.market import MarketProvider
from quantnest.domain.portfolio import Portfolio
from quantnest.application.commands.wallet_commands import CreditWalletCommand, DebitWalletCommand
from quantnest.application.commands.portfolio_commands import BuyAssetCommand, SellAssetCommand


class CreditWalletHandler:
    """Handle credit wallet commands."""
    
    def handle(self, command: CreditWalletCommand) -> Dict[str, Any]:
        """Execute credit command."""
        wallet = Wallet(command.wallet_id)
        wallet.credit(command.amount, command.transaction_id)
        
        return {
            "wallet_id": command.wallet_id,
            "amount": float(command.amount),
            "transaction_id": command.transaction_id,
            "new_balance": float(wallet.balance),
            "message": f"Successfully credited ₹{command.amount} to wallet {command.wallet_id}"
        }


class DebitWalletHandler:
    """Handle debit wallet commands."""
    
    def handle(self, command: DebitWalletCommand) -> Dict[str, Any]:
        """Execute debit command."""
        wallet = Wallet(command.wallet_id)
        wallet.debit(command.amount, command.transaction_id)
        
        return {
            "wallet_id": command.wallet_id,
            "amount": float(command.amount),
            "transaction_id": command.transaction_id,
            "new_balance": float(wallet.balance),
            "message": f"Successfully debited ₹{command.amount} from wallet {command.wallet_id}"
        }


class BuyAssetHandler:
    """Handle buy asset commands."""
    
    def handle(self, command: BuyAssetCommand) -> Dict[str, Any]:
        """Execute buy command."""
        market = MarketProvider()
        portfolio = Portfolio(command.wallet_id, market)
        portfolio.buy(command.symbol, command.quantity, command.transaction_id)
        
        return {
            "wallet_id": command.wallet_id,
            "symbol": command.symbol,
            "quantity": float(command.quantity),
            "transaction_id": command.transaction_id,
            "message": f"Successfully bought {command.quantity} shares of {command.symbol}",
            "portfolio_summary": {
                "cash": float(portfolio.cash()),
                "total_value": float(portfolio.total_value()),
                "positions": {k: float(v) for k, v in portfolio.positions.items()}
            }
        }


class SellAssetHandler:
    """Handle sell asset commands."""
    
    def handle(self, command: SellAssetCommand) -> Dict[str, Any]:
        """Execute sell command."""
        market = MarketProvider()
        portfolio = Portfolio(command.wallet_id, market)
        portfolio.sell(command.symbol, command.quantity, command.transaction_id)
        
        return {
            "wallet_id": command.wallet_id,
            "symbol": command.symbol,
            "quantity": float(command.quantity),
            "transaction_id": command.transaction_id,
            "message": f"Successfully sold {command.quantity} shares of {command.symbol}",
            "portfolio_summary": {
                "cash": float(portfolio.cash()),
                "total_value": float(portfolio.total_value()),
                "positions": {k: float(v) for k, v in portfolio.positions.items()}
            }
        }