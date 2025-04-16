import os
import sys
from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import (
    OrderArgs,
    BalanceAllowanceParams,
    AssetType,
    MarketOrderArgs,
    OrderType,
)
from py_clob_client.order_builder.constants import BUY, SELL

host = "https://clob.polymarket.com"
key = os.getenv("PK")
chain_id = POLYGON

# Create CLOB client and get/set API credentials
client = ClobClient(
    host,
    key=key,
    chain_id=chain_id,
    signature_type=1,
    funder="0x98b21dB8CBA5c318c32bb73aAd9Cd5C4E8F66525",
)
client.set_api_creds(client.create_or_derive_api_creds())
print(
    client.get_order_book(
        "39881899903855950095187972183395460164922040446051561494839991744856269622262"
    )
)

# Create and sign an order buying 100 YES tokens for 0.50c each
# resp = client.get_balance_allowance(
#    params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
# )
# resp = client.update_balance_allowance(
#    params=BalanceAllowanceParams(
#        asset_type=AssetType.CONDITIONAL,
#        token_id="39881899903855950095187972183395460164922040446051561494839991744856269622262",
#    )
# )

# print(resp)
resp = client.get_balance_allowance(
    params=BalanceAllowanceParams(
        asset_type=AssetType.CONDITIONAL,
        token_id="39881899903855950095187972183395460164922040446051561494839991744856269622262",
    )
)
print(resp)
resp = client.get_balance_allowance(
    params=BalanceAllowanceParams(
        asset_type=AssetType.COLLATERAL,
    )
)
print(resp)
sys.exit(0)
order_args = MarketOrderArgs(
    token_id="39881899903855950095187972183395460164922040446051561494839991744856269622262",
    amount=1,
)
signed_order = client.create_market_order(order_args)
resp = client.post_order(signed_order, orderType=OrderType.FOK)
print(resp)
makingAmount = float(resp["makingAmount"])
takingAmount = float(resp["takingAmount"])

price = makingAmount / takingAmount
increased_price = price * 1.1
order_args = OrderArgs(
    price=increased_price,
    size=takingAmount - 1e-6,
    side=SELL,
    token_id="39881899903855950095187972183395460164922040446051561494839991744856269622262",
)
signed_order = client.create_order(order_args)
client.update_balance_allowance(
    params=BalanceAllowanceParams(
        asset_type=AssetType.CONDITIONAL,
        token_id="39881899903855950095187972183395460164922040446051561494839991744856269622262",
    )
)
resp = client.post_order(signed_order)
print(resp)
print("Done!")

resp = client.get_balance_allowance(
    params=BalanceAllowanceParams(
        asset_type=AssetType.CONDITIONAL,
        token_id="39881899903855950095187972183395460164922040446051561494839991744856269622262",
    )
)
print(resp)
