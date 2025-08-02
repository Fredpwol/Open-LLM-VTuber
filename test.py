import requests
import json
from datetime import datetime
import time

# CoinGecko API base URL
COINGECKO_API = "https://api.coingecko.com/api/v3"

def fetch_trending_solana_memecoins():
    """
    Fetch top trending Solana memecoins from CoinGecko.
    Returns a list of memecoin data.
    """
    try:
        url = f"{COINGECKO_API}/search/trending?vs_currency=usd"
        response = requests.get(url)
        response.raise_for_status()
        trending = response.json().get('coins', [])
        
        # Filter for Solana-based memecoins
        tokens = [
            coin['item'] for coin in trending 

        ]
        
        return tokens  # Return top 5 trending
    except requests.RequestException as e:
        print(f"Error fetching trending memecoins: {e}")
        return []

def fetch_market_data():
    """
    Fetch general market data for Solana ecosystem from CoinGecko.
    Returns market cap, volume, and price change data.
    """
    try:
        url = f"{COINGECKO_API}/global"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get('data', {})
        
        # Fetch Solana-specific market data
        solana_url = f"{COINGECKO_API}/coins/solana"
        solana_response = requests.get(solana_url)
        solana_response.raise_for_status()
        solana_data = solana_response.json()
        
        market_data = {
            'total_market_cap_usd': data.get('total_market_cap', {}).get('usd', 0),
            'solana_price_usd': solana_data.get('market_data', {}).get('current_price', {}).get('usd', 0),
            'solana_24h_volume_usd': solana_data.get('market_data', {}).get('total_volume', {}).get('usd', 0),
            'solana_24h_change': solana_data.get('market_data', {}).get('price_change_percentage_24h', 0)
        }
        return market_data
    except requests.RequestException as e:
        print(f"Error fetching market data: {e}")
        return {}

def main():
    # Fetch trending Solana memecoins
    print("Fetching top trending Solana memecoins...")
    trending_memecoins = fetch_trending_solana_memecoins()
    print("\nTop Trending Solana Memecoins:")
    for coin in trending_memecoins:
        print(f"- {coin['name']} ({coin['symbol']}): ${coin["data"]['price']:.4f}, \
Market Cap: ${coin["data"]['market_cap']}, \
Price Change Percentage 24 hours: {coin['data']['price_change_percentage_24h']['usd']}% \
Total Volume: ${coin['data']['total_volume']}")

    # Fetch general market data
    print("\nFetching Solana market data...")
    market_data = fetch_market_data()
    print("\nSolana Market Data:")
    print(f"- Total Crypto Market Cap: ${market_data['total_market_cap_usd']:,.2f}")
    print(f"- Solana Price: ${market_data['solana_price_usd']:.2f}")
    print(f"- Solana 24h Volume: ${market_data['solana_24h_volume_usd']:,.2f}")
    print(f"- Solana 24h Price Change: {market_data['solana_24h_change']:.2f}%")

    main()
