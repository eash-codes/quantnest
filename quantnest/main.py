from decimal import Decimal
from quantnest.domain.wallet import Wallet

wallet = Wallet("user-1")
wallet.credit(Decimal("500"))
wallet.debit(Decimal("200"))

print("Balance:", wallet.balance)
print("Events:", len(wallet.events))
