import httpx
import json
from pprint import pprint as pp

if __name__ == "__main__":
    result_empty = False
    result_json = []
    offset = 0
    limit = 100
    while not result_empty:
        url = f"https://gamma-api.polymarket.com/markets?limit={limit:d}&active=true&closed=False&offset={offset:d}&liquidity_num_min=0"
        res = httpx.get(url)
        data = res.json()
        result_empty = len(data) == 0
        result_json.extend(data)
        offset += limit
        pp(data)
    json.dump(result_json, open("markets.json", "w"), indent=2)
