"""Portfolio manages asset positions, delegates money to Wallet."""

from decimal import Decimal
from typing import Dict, List
from .wallet import Wallet
from .market import MarketProvider, UnknownSymbolError
from .trade import Trade

class Portfolio:
    def __init__(self, wallet_id: str,market: MarketProvider):
        self._wallet = Wallet(wallet_id)
        self._market = market
        self._positions:Dict[str, Decimal] = {}
        self._trades: List[Trade] =[]
        

        @property
        def positions(self) -> Dict[str, Decimal] :
            return self._positions.copy()
        @property
        def trades(self) -> List[Trade] :
            return self._trades.copy()
        
        def buy(self, symbol: str, quantity: Decimal) -> None:
            """"Buy quantity of symbol if sufficient funds exist"""
            if quantity<= 0:
                raise ValueError("Quantity must be positive")
            
            price= self.market.get_price(symbol)
            cost = price * quantity

            
            self.wallet.debit(cost)
            self._positions[symbol] = self._positions.get(symbol, 0) + quantity

            trade = Trade(symbol, "BUY", quantity,price)
            self.trades.append(trade)

        def sell(self,symbol: str,quantity: Decimal) ->None:
            """Sell quantity of a stock or symbol if owned"""

            if quantity <=0:
                raise ValueError("Quantity must be positive")
            
            owned = self._positions.get(symbol, 0)
            if quantity > owned :
                raise ValueError(f"cannot seld {quantity},own only {owned}")
            
            price =self.market.get_price(symbol)
            proceeds = price * quantity

            self.wallet.credit(proceeds)

            self._positions[symbol] -= quantity
            if self._positions[symbol] == 0:
                del self._positions[symbol]

            trade = Trade(symbol, "SELL", quantity, proceeds)
            self.trades.append(trade)