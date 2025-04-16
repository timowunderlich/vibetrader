import os
import json
import httpx
import logging
import argparse
from time import sleep, time
from datetime import datetime, timedelta, timezone
from typing import List

from truthbrush.api import Api as TruthBrushAPI
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
from vllm import LLM


class VibeTrader:
    def __init__(
        self,
        markets: List[dict],
        ts_username: str,
        ts_password: str,
        ts_account_to_watch: str,
        clob_private_key: str,
        clob_wallet_address: str,
        poll_interval: float = 8.0,
        clob_host: str = "https://clob.polymarket.com",
        llm_model="facebook/opt-125m",
        logger=None,
        sell_multiplier: float = None,
        amount_to_buy: float = None,
    ):
        self.markets = markets
        self.ts_username = ts_username
        self.ts_password = ts_password
        self.ts_account_to_watch = ts_account_to_watch
        self.clob_private_key = clob_private_key
        self.clob_wallet_address = clob_wallet_address
        self.poll_interval = poll_interval
        self.clob_host = clob_host
        self.sell_multiplier = sell_multiplier
        self.amount_to_buy = amount_to_buy

        self._responses = ["rise", "fall", "neutral"]
        self._movement_responses = ["rise", "fall"]

        self.clob_client = ClobClient(
            self.clob_host,
            key=self.clob_private_key,
            chain_id=POLYGON,
            signature_type=1,
            funder=self.clob_wallet_address,
        )
        self.clob_client.set_api_creds(self.clob_client.create_or_derive_api_creds())

        self.llm = LLM(model=llm_model)

        self.ts_api = TruthBrushAPI(
            username=self.ts_username,
            password=self.ts_password,
        )

        if logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.INFO)

    @staticmethod
    def get_prompt(market: str, date: datetime, text: str, image_url: str = None):
        prompt = "Your job is to determine whether a social media post will cause a given prediction market to rise or fall. "
        +"Respond with 'rise' if you think the market will significantly rise, 'fall' if you think the market will "
        +"significantly fall, or 'neutral' if you think the tweet will have no effect on the market. Only respond "
        +"with 'rise' or 'fall' if you are confident in your prediction and the movement is likely to be significant. "
        +f"Market: {market}. Post date: {date}. Post text: '{text}'.",
        # TODO: download image and add to prompt
        if image_url is not None:
            print("WARNING: Image URL is not None, but image is not added to prompt")
        return prompt

    def process_completions(self, prompts: List[str]):
        completions = self.llm.generate(prompts)
        return [completion.outputs[0].text for completion in completions]

    @staticmethod
    def get_current_time():
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        return now

    def process_moved_markets(
        self, moved_markets: List[dict], movement_directions: List[str]
    ):
        for market, direction in zip(moved_markets, movement_directions):
            self.logger.info(f"Market: {market['question']}, Direction: {direction}")
            if direction == "rise":
                self.logger.info("Market is expected to rise, buying 'Yes' token")
            elif direction == "fall":
                self.logger.info("Market is expected to fall, buying 'No' token")
            else:
                self.logger.error(f"Invalid direction: {direction}")
                continue

            assert json.loads(market["outcomes"]) == ["Yes", "No"]
            token_ids = json.loads(market["clobTokenIds"])
            if direction == "rise":
                buy_token_id = token_ids[0]
            elif direction == "fall":
                buy_token_id = token_ids[1]
            if self.amount_to_buy is not None:
                amount = self.amount_to_buy
            else:
                # poll balance
                collateral_params = BalanceAllowanceParams(
                    asset_type=AssetType.COLLATERAL,
                )
                clob_client.update_balance_allowance(params=collateral_params)
                resp = clob_client.get_balance_allowance(params=collateral_params)
                balance = (float(resp["balance"])) / 1e6
                # round down to 3 decimal places
                amount = round(balance, 3)
            market_order_args = MarketOrderArgs(
                token_id=buy_token_id,
                amount=amount,
            )
            signed_order = clob_client.create_market_order(market_order_args)
            resp = clob_client.post_order(signed_order, orderType=OrderType.FOK)
            if not resp["success"]:
                self.logger.error(f"Failed to post market order: {resp}")
                break
            else:
                self.logger.info(f"Market order success: {resp}")
            making_amount = float(resp["makingAmount"])
            taking_amount = float(resp["takingAmount"])
            price = making_amount / taking_amount

            if self.sell_multiplier is not None:
                increased_price = price * self.sell_multiplier
                order_args = OrderArgs(
                    price=increased_price,
                    size=taking_amount - 1e-6,
                    side=SELL,
                    token_id=buy_token_id,
                )
                signed_order = clob_client.create_order(order_args)
                clob_client.update_balance_allowance(
                    params=BalanceAllowanceParams(
                        asset_type=AssetType.CONDITIONAL,
                        token_id=buy_token_id,
                    )
                )
                resp = clob_client.post_order(signed_order, orderType=OrderType.GTC)
                if not resp["success"]:
                    self.logger.error(f"Failed to post sell order: {resp}")
                    break
                else:
                    self.logger.info(f"Sell order success: {resp}")

    def __call__(self):
        self.run()

    def run(self):
        created_after = self.get_current_time()
        while True:
            start_time = time()
            self.logger.info(f"Polling statuses created after {created_after}")
            try:
                statuses = list(
                    self.ts_api.pull_statuses(
                        self.ts_account_to_watch,
                        created_after=created_after,
                    )
                )
            except:
                self.logger.error(f"Error: {e}. Sleeping for 60 seconds")
                sleep(60)
                continue
            self.logger.info(f"Received {len(statuses)} statuses")
            for status in statuses:
                media_attachments = status["media_attachments"]
                status_content = status["content"]
                # strip <p> and </p> tags
                status_content = status_content.replace("<p>", "").replace("</p>", "")
                # remove content within <a> tags
                while "<a" in status_content:
                    start = status_content.index("<a")
                    end = status_content.index("</a>", start)
                    status_content = status_content[:start] + status_content[end + 4 :]
                self.logger.info(f"Status content: {status_content}")
                if status["reblog"] is not None:
                    self.logger.info("Status is a reblog, skipping")
                    continue

                if len(status_content) == 0:
                    self.logger.info("Empty status content, skipping")
                    continue
                if len(media_attachments) > 0:
                    if media_attachments[0]["type"] == "image":
                        image_url = media_attachments[0]["url"]

                all_prompts = list()
                for tmp_m in markets:
                    prompt = get_prompt(
                        market=tmp_m["question"],
                        date=datetime.fromisoformat(
                            status["created_at"].replace("Z", "+00:00")
                        ),
                        text=status_content,
                        image_url=image_url,
                    )
                    all_prompts.append(prompt)
                completions = process_completions(all_prompts)
                self.logger.info(f"Status: {status_content}")
                moved_markets = list()
                movement_directions = list()
                for market, completion in zip(markets, completions):
                    if completion not in self._responses:
                        self.logger.error(f"Invalid completion: {completion}")
                        continue
                    self.logger.info(
                        f"Market: {market['question']}, Completion: {completion}"
                    )
                    if completion in self._movement_responses:
                        moved_markets.append(market)
                        movement_directions.append(completion)
                process_moved_markets(moved_markets, movement_directions)

            if len(statuses) > 0:
                created_after = get_current_time()
            end_time = time()
            if end_time - start_time < self.poll_interval:
                sleep(self.poll_interval - (end_time - start_time))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--markets",
        type=str,
        default="filtered_markets.json",
        help="Path to markets file",
    )
    parser.add_argument(
        "--poll_interval",
        type=float,
        default=8.0,
        help="Polling interval in seconds",
    )
    parser.add_argument(
        "--sell_multiplier",
        type=float,
        default=None,
        help="Sell multiplier. Places a sell order at this price times the buy price",
    )
    parser.add_argument(
        "--amount_to_buy",
        type=float,
        default=None,
        help="Amount to buy in USDC. If None, buys using all available USDC",
    )
    parser.add_argument(
        "--llm_model",
        type=str,
        default="facebook/opt-125m",
        help="LLM model to use",
    )
    parser.add_argument(
        "--clob_host",
        type=str,
        default="https://clob.polymarket.com",
        help="CLOB host",
    )
    parser.add_argument(
        "--clob_private_key",
        type=str,
        default=None,
        help="CLOB private key",
        required=True,
    )
    parser.add_argument(
        "--clob_wallet_address",
        type=str,
        default=None,
        help="CLOB wallet address",
        required=True,
    )
    parser.add_argument(
        "--ts_username",
        type=str,
        default=None,
        help="Truth Social username",
        required=True,
    )
    parser.add_argument(
        "--ts_password",
        type=str,
        default=None,
        help="Truth Social password",
        required=True,
    )
    parser.add_argument(
        "--ts_account_to_watch",
        type=str,
        default=None,
        help="Truth Social account to watch",
        required=True,
    )

    args = parser.parse_args()
    if not os.path.exists(args.markets):
        raise RuntimeError(f"{args.market} not found. Create using get_markets.py")
    markets = json.loads(open(args.market).read())
    vibetrader = VibeTrader(
        markets=markets,
        ts_username=args.ts_username,
        ts_password=args.ts_password,
        ts_account_to_watch=args.ts_account_to_watch,
        clob_private_key=args.clob_private_key,
        clob_wallet_address=args.clob_wallet_address,
        poll_interval=args.poll_interval,
        clob_host=args.clob_host,
        llm_model=args.llm_model,
        sell_multiplier=args.sell_multiplier,
        amount_to_buy=args.amount_to_buy,
    )
    vibetrader()
