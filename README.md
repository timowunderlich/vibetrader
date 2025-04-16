![](logo.svg)

## Description
VibeTrader performs trades on prediction markets using LLM-based sentiment analysis.
It polls for new posts of a specified user on Truth Social and dispatches buy orders on Polymarket according to the result of a LLM query. The LLM is asked to predict whether a given prediction market will rise or fall as a result of the new post and market buy orders are dispatched accordingly. 

## Installation
Install requirements:
```
pip install -r requirements.txt
```

## Usage
You need to supply Truth Social credentials (`--ts_username`, `--ts_password`) and the user to watch (`--ts_account_to_watch`) and the private key for a wallet on the Polygon chain (`--clob_private_key`, `--clob_wallet_address`). The markets to check are passed using a JSON file (`--market`); use the Python script `get_markets.py` to get all markets and filter for your use case. 
```
$ python vibetrader.py --help
usage: vibetrader.py [-h] [--markets MARKETS] [--poll_interval POLL_INTERVAL] [--sell_multiplier SELL_MULTIPLIER] [--amount_to_buy AMOUNT_TO_BUY] [--llm_model LLM_MODEL] [--clob_host CLOB_HOST] --clob_private_key CLOB_PRIVATE_KEY
                     --clob_wallet_address CLOB_WALLET_ADDRESS --ts_username TS_USERNAME --ts_password TS_PASSWORD --ts_account_to_watch TS_ACCOUNT_TO_WATCH

options:
  -h, --help            show this help message and exit
  --markets MARKETS     Path to markets file
  --poll_interval POLL_INTERVAL
                        Polling interval in seconds
  --sell_multiplier SELL_MULTIPLIER
                        Sell multiplier. Places a sell order at this price times the buy price
  --amount_to_buy AMOUNT_TO_BUY
                        Amount to buy in USDC. If None, buys using all available USDC
  --llm_model LLM_MODEL
                        LLM model to use
  --clob_host CLOB_HOST
                        CLOB host
  --clob_private_key CLOB_PRIVATE_KEY
                        CLOB private key
  --clob_wallet_address CLOB_WALLET_ADDRESS
                        CLOB wallet address
  --ts_username TS_USERNAME
                        Truth Social username
  --ts_password TS_PASSWORD
                        Truth Social password
  --ts_account_to_watch TS_ACCOUNT_TO_WATCH
                        Truth Social account to watch
```