"""Stock Geographic Mapping — Exchange → lat/lon for 3D Globe visualization."""

# Exchange → (latitude, longitude) mapping for globe markers
EXCHANGE_COORDS = {
    # US Exchanges
    "NMS": (40.7, -74.0),      # NASDAQ (New York)
    "NYQ": (40.7, -74.0),      # NYSE
    "NGM": (40.7, -74.0),      # NASDAQ Global Market
    "NAS": (40.7, -74.0),      # NASDAQ
    "NASDAQ": (40.7, -74.0),
    "NYSE": (40.7, -74.0),
    "PCX": (37.8, -122.4),     # NYSE Arca (San Francisco)
    "BTS": (40.7, -74.0),      # BATS
    "CCC": (40.7, -74.0),      # Crypto (default US)
    
    # European Exchanges
    "LSE": (51.5, -0.1),       # London
    "FRA": (50.1, 8.7),        # Frankfurt
    "PAR": (48.9, 2.3),        # Paris (Euronext)
    "AMS": (52.4, 4.9),        # Amsterdam
    "STO": (59.3, 18.1),       # Stockholm
    "MIL": (45.5, 9.2),        # Milan
    "SWX": (47.4, 8.5),        # Swiss Exchange
    "MCE": (40.4, -3.7),       # Madrid
    
    # Asia-Pacific Exchanges
    "TYO": (35.7, 139.7),      # Tokyo
    "HKG": (22.3, 114.2),      # Hong Kong
    "SHH": (31.2, 121.5),      # Shanghai
    "SHZ": (22.5, 114.1),      # Shenzhen
    "NSI": (19.1, 72.9),       # NSE India (Mumbai)
    "BSE": (19.1, 72.9),       # BSE India (Mumbai)
    "KSC": (37.6, 127.0),      # Korea (Seoul)
    "TAI": (25.0, 121.5),      # Taiwan
    "ASX": (-33.9, 151.2),     # Australia (Sydney)
    "SGX": (1.3, 103.8),       # Singapore
    "SET": (13.8, 100.5),      # Thailand (Bangkok)
    "JKT": (-6.2, 106.8),      # Jakarta
    
    # Americas (non-US)
    "SAO": (-23.5, -46.6),     # São Paulo
    "TSX": (43.7, -79.4),      # Toronto
    "MEX": (19.4, -99.1),      # Mexico City
    
    # Middle East & Africa
    "TAD": (24.5, 54.7),       # Abu Dhabi
    "DFM": (25.3, 55.3),       # Dubai
    "TAE": (32.1, 34.8),       # Tel Aviv
    "JSE": (-26.2, 28.0),      # Johannesburg
}

# Ticker suffix → exchange mapping for yfinance tickers
SUFFIX_TO_EXCHANGE = {
    ".NS": "NSI",
    ".BO": "BSE",
    ".L": "LSE",
    ".T": "TYO",
    ".HK": "HKG",
    ".SS": "SHH",
    ".SZ": "SHZ",
    ".AX": "ASX",
    ".DE": "FRA",
    ".PA": "PAR",
    ".TO": "TSX",
    ".SA": "SAO",
    ".KS": "KSC",
    ".TW": "TAI",
    ".SI": "SGX",
}


def get_coords_for_ticker(ticker: str, exchange: str = "") -> tuple[float, float]:
    """Get lat/lon for a ticker based on its exchange or suffix."""
    import hashlib
    
    # Check suffix first
    for suffix, ex_code in SUFFIX_TO_EXCHANGE.items():
        if ticker.upper().endswith(suffix):
            return EXCHANGE_COORDS.get(ex_code, (40.7, -74.0))
    
    # Hash ticker to deterministically spread fallbacks so they don't stack
    h = int(hashlib.md5(ticker.encode()).hexdigest(), 16)
    
    # Crypto defaults - spread across decentralized tech hubs
    crypto_hubs = [
        (37.8, -122.4),  # SF/Silicon Valley
        (25.8, -80.2),   # Miami
        (47.2, 8.5),     # Zug (Crypto Valley)
        (1.3, 103.8),    # Singapore
        (52.5, 13.4),    # Berlin
        (35.7, 139.7)    # Tokyo
    ]
    if "-USD" in ticker.upper() or "USDT" in ticker.upper():
        return crypto_hubs[h % len(crypto_hubs)]
    
    # Try exchange name
    if exchange:
        ex_upper = exchange.upper()
        if ex_upper in EXCHANGE_COORDS:
            return EXCHANGE_COORDS[ex_upper]
        # Try partial match
        for key, coords in EXCHANGE_COORDS.items():
            if key in ex_upper or ex_upper in key:
                return coords
                
    # Default global financial hubs for international fallbacks instead of just NYC
    global_hubs = [
        (40.7, -74.0),   # NYC
        (51.5, -0.1),    # London
        (35.7, 139.7),   # Tokyo
        (48.9, 2.3),     # Paris
        (50.1, 8.7),     # Frankfurt
        (22.3, 114.2),   # Hong Kong
        (31.2, 121.5),   # Shanghai
        (1.3, 103.8),    # Singapore
        (-33.9, 151.2),  # Sydney
        (-23.5, -46.6),  # Sao Paulo
        (25.3, 55.3),    # Dubai
        (19.1, 72.9)     # Mumbai
    ]
    
    return global_hubs[h % len(global_hubs)]


def format_market_cap(mcap: float) -> str:
    """Format market cap to human-readable string."""
    if not mcap or mcap == 0:
        return "N/A"
    if mcap >= 1e12:
        return f"${mcap/1e12:.1f}T"
    if mcap >= 1e9:
        return f"${mcap/1e9:.1f}B"
    if mcap >= 1e6:
        return f"${mcap/1e6:.0f}M"
    return f"${mcap:,.0f}"


def format_volume(vol: float) -> str:
    """Format volume to human-readable string."""
    if not vol or vol == 0:
        return "N/A"
    if vol >= 1e9:
        return f"{vol/1e9:.1f}B"
    if vol >= 1e6:
        return f"{vol/1e6:.0f}M"
    if vol >= 1e3:
        return f"{vol/1e3:.0f}K"
    return str(int(vol))
