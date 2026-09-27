"""Fetch the forecast for a place from the weather service and print a short summary."""

import sys

import httpx

API = "https://api.wetter.example/v1/forecast"


def main(place: str) -> int:
    response = httpx.get(API, params={"q": place}, timeout=10)
    response.raise_for_status()
    data = response.json()
    print(f"{place}: {data['temperature']} °C, {data['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(" ".join(sys.argv[1:]) or "Berlin"))
