import asyncio
import json
import traceback
import websockets
import re
import time
from typing import Callable, Dict, Any, List, Optional
from loguru import logger
from .live_interface import LivePlatformInterface
import base58
from collections import defaultdict, deque
import aiohttp
from aiohttp_socks import ProxyConnector

DEX_TRENDING_URL = "https://api.dexscreener.com/token-boosts/top/v1"
DEX_TOKEN_INFO_URL = "https://api.dexscreener.com/tokens/v1/{chainId}/{tokenAddresses}"
PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"
MORALIS_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjM4NTU2ZTRlLWZkYzUtNGJjMy1hNDdmLWUwMTE5NTE1ODY3YyIsIm9yZ0lkIjoiNDYwMDMxIiwidXNlcklkIjoiNDczMjg3IiwidHlwZUlkIjoiM2Y4ODIwMzItYzYxZi00YjQ4LWJhMGItNTdjMmYzNzkxYTgwIiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NTI4NDkxMTYsImV4cCI6NDkwODYwOTExNn0.y3RGggpVcpam4Fqm-_Xf-e9iVEMJiazlhTZ7ZzwZEuw"

def format_trending_tokens(tokens: list) -> str:
    """
    Format a list of trending token dicts into a readable string for AI/TTS.
    """
    lines = []
    for i, token in enumerate(tokens, 1):
        name = token.get("description", "").split("\n")[0] or "No description"
        url = token.get("url", "")
        address = token.get("tokenAddress", "")
        chain = token.get("chainId", "")
        total = token.get("totalAmount", "")
        # Try to get a Twitter or Website link
        twitter = ""
        website = ""
        for link in token.get("links", []):
            if link.get("type") == "twitter":
                twitter = link.get("url")
            if link.get("label", "").lower() == "website":
                website = link.get("url")
        # Compose summary
        summary = (
            f"{i}. {name}\n"
            f"   Chain: {chain}, Address: {address}\n"
            f"   Total Amount: {total}\n"
        )
        if website:
            summary += f"   Website: {website}\n"
        if twitter:
            summary += f"   Twitter: {twitter}\n"
        lines.append(summary)
    return "\n".join(lines)

class PumpFunLivePlatform(LivePlatformInterface):
    """
    Implementation of LivePlatformInterface for Pump.fun Live chat.
    Connects to pump.fun (reverse-engineered) and forwards messages to the VTuber.
    """
    def __init__(self, config):
        # super().__init__(config)
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._running = False
        self._message_handlers: List[Callable[[Dict[str, Any]], None]] = []
        self.room_id = config.get("room_id", "")
        self.limit = config.get("limit", 20)
        self.last_timestamp = int(time.time() * 1000)

    @property
    def is_connected(self) -> bool:
        try:
            if hasattr(self._websocket, "closed"):
                return self._connected and self._websocket and not self._websocket.closed
            elif hasattr(self._websocket, "open"):
                return self._connected and self._websocket and self._websocket.open
            else:
                return self._connected and self._websocket is not None
        except Exception:
            return False

    async def connect(self, proxy_url: str = "ws://localhost:12393/proxy-ws") -> bool:
        try:
            self._websocket = await websockets.connect(
                proxy_url, ping_interval=20, ping_timeout=10, close_timeout=5
            )
            self._connected = True
            logger.info(f"Connected to proxy at {proxy_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to proxy: {e}")
            return False

    async def disconnect(self) -> None:
        self._running = False
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"Error while closing WebSocket: {e}")
        self._connected = False
        logger.info("Disconnected from Pump.fun Live and proxy server")

    async def send_message(self, text: str) -> bool:
        logger.warning("Pump.fun Live platform doesn't support sending messages back to the live room")
        return False

    async def register_message_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        self._message_handlers.append(handler)
        logger.debug("Registered new message handler")

    async def _send_to_proxy(self, text: str, priority=None) -> bool:
        if not self.is_connected:
            logger.error("Cannot send message: Not connected to proxy")
            return False
        try:
            message = {"type": "text-input", "text": text}
            await self._websocket.send(json.dumps(message))
            logger.info(f"Sent message to VTuber: {text}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to proxy: {e}")
            self._connected = False
            return False

    async def _send_system_priority_message(self, text: str) -> bool:
        if not self.is_connected:
            logger.error("Cannot send system-priority-message: Not connected to proxy")
            return False
        try:
            message = {"type": "system-priority-message", "text": text}
            await self._websocket.send(json.dumps(message))
            logger.info(f"Sent system-priority-message to VTuber: {text}")
            return True
        except Exception as e:
            logger.error(f"Error sending system-priority-message to proxy: {e}")
            self._connected = False
            return False

    async def start_receiving(self) -> None:
        if not self.is_connected:
            logger.error("Cannot start receiving: Not connected to proxy")
            return
        try:
            logger.info("Started receiving messages from proxy")
            while self._running and self.is_connected:
                try:
                    message = await self._websocket.recv()
                    data = json.loads(message)
                    logger.debug(f"Received message from VTuber: {data}")
                    await self.handle_incoming_messages(data)
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed by server")
                    self._connected = False
                    break
                except Exception as e:
                    logger.error(f"Error receiving message from proxy: {e}")
                    await asyncio.sleep(1)
            logger.info("Stopped receiving messages from proxy")
        except Exception as e:
            logger.error(f"Error in message receiving loop: {e}")

    async def handle_incoming_messages(self, message: Dict[str, Any]) -> None:
        for handler in self._message_handlers:
            try:
                await asyncio.to_thread(handler, message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    async def keepalive(self, ws, interval=20):
        while True:
            try:
                await ws.send("2")  # Socket.io ping
                await asyncio.sleep(interval)
            except Exception:
                break

    async def fetch_pumpfun_messages(self):
        ws_url = "wss://livechat.pump.fun/socket.io/?EIO=4&transport=websocket"
        last_timestamp = int(time.time() * 1000)
        count = 420
        # --- Per-user recent message cache for spam detection ---
        user_message_cache = defaultdict(lambda: deque(maxlen=5))  # last 5 messages per user
        socks_proxy = "socks5://spxwbpjc1q:Gb7wwn34gjr5YR~bFx@us.decodo.com:10000"

        while self._running:
            try:
                connector = ProxyConnector.from_url(socks_proxy)
                session = aiohttp.ClientSession(connector=connector)
                async with session.ws_connect(ws_url) as ws:
                    await ws.send_str("40")  # Socket.io handshake
                    await asyncio.sleep(0.5)
                    # Join the room
                    join_room = ["joinRoom", {"roomId": self.room_id, "username": ""}]
                    await ws.send_str(f'{count}{json.dumps(join_room)}')
                    count += 1
                    await asyncio.sleep(0.2)
                    # Request message history


                    # Start keepalive task
                    keepalive_task = asyncio.create_task(self.keepalive(ws))

                    try:
                        while self._running:
                            try:
                                req = ["getMessageHistory", {"roomId": self.room_id, "before": last_timestamp, "limit": self.limit}]
                                await ws.send_str(f'{count}{json.dumps(req)}')
                                count += 1
                                msg = await asyncio.wait_for(asyncio.shield(ws.receive()), timeout=100000)
                                if not msg:
                                    continue
                                try:
                                    match = re.match(r'^(\d+)(.*)', msg.data)
                                except TypeError:
                                    continue
                                if match:
                                    number = match.group(1)
                                    rest = match.group(2)
                                else:
                                    continue
                                try:
                                    body = json.loads(rest)
                                except:
                                    continue
                                messages = []
                                if type(body) == list:
                                    if type(body[0]) == list and all([
                                        msgkey in body[0][0] for msgkey in ["username", "id", "userAddress", "roomId", "message", "messageType"]
                                    ]):
                                        messages = body[0]
                                    elif "newMessage" in body and type(body[1]) == dict:
                                        messages = [body[1]]
                                for message in messages:
                                    text = message.get("message", "")
                                    username = message.get("username", "")
                                    # --- Solana address check (base58, 32-44+ chars, no 0/O/I/l) ---
                                    is_solana = False
                                    if 32 <= len(username) <= 44:
                                        try:
                                            base58.b58decode(username)
                                            is_solana = True
                                        except Exception:
                                            is_solana = False
                                    display_name = "viewer" if is_solana else username
                                    # --- Spam/Promotion/Unreadable filter ---
                                    if not text.strip():
                                        continue  # skip empty
                                    if sum(1 for c in text if ord(c) > 127) > len(text) // 2:
                                        continue
                                    promo_keywords = ["http://", "https://", "www.", "discord.gg", "join now", "pump.fun", "airdrop", "giveaway", "free", "win", "bonus", "referral", "invite", "promo", "shill", "follow", "subscribe", "telegram", "t.me", "$", "coin", "token", "project", "mint", "presale", "launch", "buy now", "buy", "sell", "exchange", "listing", "exchange", "binance", "okx", "bybit", "kucoin", "bitget", "gate.io"]
                                    lowered = text.lower()
                                    if any(kw in lowered for kw in promo_keywords):
                                        continue
                                    if len(set(text)) < 3 or len(text) < 3:
                                        continue
                                    if text.isupper() and len(text) > 6:
                                        continue
                                    emoji_count = sum(1 for c in text if ord(c) > 10000)
                                    if emoji_count > len(text) // 2:
                                        continue
                                    # --- Per-user repeated message spam filter ---
                                    cache = user_message_cache[username]
                                    if text in cache:
                                        continue  # skip repeated message from this user
                                    cache.append(text)
                                    
                                    yield f"{display_name + ' (Viewer)' if not is_solana else display_name }: {text}"
                                    await asyncio.sleep(0.5)
                            except asyncio.TimeoutError:
                                continue
                    finally:
                        keepalive_task.cancel()
                        try:
                            await keepalive_task
                        except asyncio.CancelledError:
                            pass
                await session.close()
            except Exception as e:
                await session.close()
                print(traceback.format_exc())
                logger.error(f"Error in fetch_pumpfun_messages: {e}")
                logger.info("Reconnecting to pump.fun websocket in 5 seconds...")
                await asyncio.sleep(5)

    async def fetch_trending_tokens(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(DEX_TRENDING_URL) as resp:
                data = await resp.json()
                return data

    async def fetch_token_info(self, chain_id, token_address):
        """
        Fetch token info using Moralis Solana token metadata API.
        https://docs.moralis.com/web3-data-api/solana/reference/get-token-metadata
        """
        MORALIS_API_URL = f"https://solana-gateway.moralis.io/token/mainnet/{token_address}/metadata"
        token_analytics = f'https://deep-index.moralis.io/api/v2.2/tokens/{token_address}/analytics?chain=solana'
        headers = {
            'X-API-KEY': MORALIS_API_KEY
            # Add your Moralis API key here if required, e.g. 'X-API-Key': 'YOUR_API_KEY'
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(MORALIS_API_URL, headers=headers) as resp:
                    token_metadata = await resp.json()
                async with session.get(token_analytics, headers=headers) as resp:
                    token_analytics = await resp.json()
                token_metadata["analytics"] = token_analytics
                return token_metadata
        except Exception as e:
            logger.error(f"Error fetching token info from Moralis: {e}")
            return None

    async def monitor_trending_tokens(self, interval=1500):
        while self._running:
            trending = await self.fetch_trending_tokens()
            # trending is expected to be a dict with a 'data' key containing the list
            tokens = trending.get('data', trending) if isinstance(trending, dict) else trending
            msg = f"[SYSTEM] Trending tokens:\n{format_trending_tokens(tokens)}"
            await self._send_system_priority_message(msg)
            await asyncio.sleep(interval)

    async def monitor_token_info(self, chain_id, token_address, interval=900):
        while self._running:
            info = await self.fetch_token_info(chain_id, token_address)
            msg = f"[SYSTEM] Token info for your token; feel free to comment about it {token_address}: {info}"
            await self._send_system_priority_message(msg)
            await asyncio.sleep(interval)

    async def listen_token_migration(self, token_address):
        try:
            async with websockets.connect(PUMPPORTAL_WS) as ws:
                payload = {"method": "subscribeMigration", "keys": [token_address]}
                await ws.send(json.dumps(payload))
                async for message in ws:
                    data = json.loads(message)
                    if data.get("method") == "subscribeMigration":
                        msg = f"[SYSTEM] Token migration event: {data}"
                        await self._send_system_priority_message(msg)
        except Exception as e:
            logger.error(f"Error in listen_token_migration: {e}")

    async def fetch_solana_market_data(self):
        """
        Fetch general market data for Solana ecosystem from CoinGecko.
        Returns a dict with market cap, volume, price, and 24h change.
        """
        COINGECKO_API = "https://api.coingecko.com/api/v3"
        try:
            async with aiohttp.ClientSession() as session:
                # Global market data
                async with session.get(f"{COINGECKO_API}/global") as resp:
                    data = await resp.json()
                # Solana-specific data
                async with session.get(f"{COINGECKO_API}/coins/solana") as sol_resp:
                    solana_data = await sol_resp.json()
                market_data = {
                    'total_market_cap_usd': data.get('data', {}).get('total_market_cap', {}).get('usd', 0),
                    'solana_price_usd': solana_data.get('market_data', {}).get('current_price', {}).get('usd', 0),
                    'solana_24h_volume_usd': solana_data.get('market_data', {}).get('total_volume', {}).get('usd', 0),
                    'solana_24h_change': solana_data.get('market_data', {}).get('price_change_percentage_24h', 0)
                }
                return market_data
        except Exception as e:
            logger.error(f"Error fetching Solana market data: {e}")
            return {}

    async def monitor_solana_market_data(self, interval=3600):
        """
        Periodically fetch Solana market data and send as a system-priority message every hour.
        """
        while self._running:
            data = await self.fetch_solana_market_data()
            if data:
                msg = (
                    f"[SYSTEM] Solana Market Update:\n"
                    f"- Total Crypto Market Cap: ${data['total_market_cap_usd']:,.2f}\n"
                    f"- Solana Price: ${data['solana_price_usd']:.2f}\n"
                    f"- Solana 24h Volume: ${data['solana_24h_volume_usd']:,.2f}\n"
                    f"- Solana 24h Price Change: {data['solana_24h_change']:.2f}%"
                )
                await self._send_system_priority_message(msg)
            await asyncio.sleep(interval)

    async def fetch_and_format_crypto_news(self, max_articles=3, max_desc_len=1000):
        """
        Fetch crypto news from Newsdata.io and format for system message.
        """
        NEWS_API_KEY = "pub_76f9497c847b4d46a7844ae27e2343d1"
        NEWS_API_URL = "https://newsdata.io/api/1/news"
        params = {
            "apikey": NEWS_API_KEY,
            "q": "crypto",
            "language": "en"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(NEWS_API_URL, params=params) as resp:
                    data = await resp.json()
                    articles = data.get("results", [])[:max_articles]
                    formatted = []
                    for art in articles:
                        title = art.get("title", "No Title")
                        source = art.get("source_id", "Unknown Source")
                        date = art.get("pubDate", "")[:10]
                        desc = art.get("description", "") or art.get("content", "")
                        desc = (desc[:max_desc_len] + "...") if len(desc) > max_desc_len else desc
                        url = art.get("link", "")
                        formatted.append(
                            f"{title}\n{source} - {date}\n{desc}"
                        )
                    return "\n\n".join(formatted) if formatted else "No recent crypto news found."
        except Exception as e:
            logger.error(f"Error fetching crypto news: {e}")
            return "[SYSTEM] Error fetching crypto news."

    async def monitor_crypto_news(self, interval=3600):
        """
        Periodically fetch and send crypto news as a system-priority message every hour.
        """
        while self._running:
            news = await self.fetch_and_format_crypto_news()
            msg = f"[SYSTEM] Crypto News Update:\n{news}"
            await self._send_system_priority_message(msg)
            await asyncio.sleep(interval)

    async def run(self) -> None:
        proxy_url = "ws://localhost:12393/proxy-ws"
        try:
            self._running = True
            # --- Start background info tasks ---
            chain_id = "solana"  # Or get from config
            token_address = self.room_id
            asyncio.create_task(self.monitor_trending_tokens())
            asyncio.create_task(self.monitor_token_info(chain_id, token_address))
            asyncio.create_task(self.listen_token_migration(token_address))
            asyncio.create_task(self.monitor_solana_market_data())
            asyncio.create_task(self.monitor_crypto_news())
            # --- Main chat logic ---
            if not await self.connect(proxy_url):
                logger.error("Failed to connect to proxy, exiting")
                return
            receive_task = asyncio.create_task(self.start_receiving())
            logger.info("Connected to Pump.fun Live (waiting for messages)")
            try:
                async for message in self.fetch_pumpfun_messages():
                    if message:
                        await self._send_to_proxy(message)
            finally:
                if not receive_task.done():
                    receive_task.cancel()
                    try:
                        await receive_task
                    except asyncio.CancelledError:
                        pass
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            logger.error(f"Error in Pump.fun Live run loop: {e}")
        finally:
            await self.disconnect() 
