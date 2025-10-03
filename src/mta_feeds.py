# MTA GTFS-realtime feed URLs
FEEDS = {
    'ace': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',  # A, C, E, SR
    'bdfm': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',  # B, D, F, M, SF
    'g': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g',  # G
    'jz': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',  # J, Z
    'nqrw': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',  # N, Q, R, W
    'l': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l',  # L
    '1234567': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',  # 1, 2, 3, 4, 5, 6, 7, S
    'si': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si'  # SIR
}

# Map of routes to their feed keys
ROUTE_TO_FEED = {
    'A': 'ace', 'C': 'ace', 'E': 'ace', 'SR': 'ace',
    'B': 'bdfm', 'D': 'bdfm', 'F': 'bdfm', 'M': 'bdfm', 'SF': 'bdfm',  # SF is Franklin Avenue Shuttle
    'G': 'g',
    'J': 'jz', 'Z': 'jz',
    'N': 'nqrw', 'Q': 'nqrw', 'R': 'nqrw', 'W': 'nqrw',
    'L': 'l',
    '1': '1234567', '2': '1234567', '3': '1234567',
    '4': '1234567', '5': '1234567', '6': '1234567', '7': '1234567',
    'S': '1234567',  # S train belongs to 1234567 feed
    'SIR': 'si'  # SIR is the Staten Island Railway
} 