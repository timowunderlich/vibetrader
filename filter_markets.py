import json
import argparse

filter_strings = ["Trump", "Mike Johnson"]

if __name__ == "__main__":
    all_markets = json.loads(open("all_markets.json").read())
    p_cutoff = 0.1
    filtered_markets = list()
    for market in all_markets:
        outcome_prices = json.loads(market["outcomePrices"])
        if (
            float(outcome_prices[0]) < p_cutoff
            or float(outcome_prices[0]) > 1 - p_cutoff
        ):
            continue
        if "Trump" in market["question"]:
            filtered_markets.append(market)
    json.dump(filtered_markets, open("filtered_markets.json", "w"), indent=4)
