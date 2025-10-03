"""
Route data for MTA subway lines including colors and names.
"""

def load_route_data():
    """
    Returns a dictionary containing route information for all MTA subway lines.
    Each route entry includes:
    - color: Hex color code for the route
    - text_color: Hex color code for text (white or black)
    - name: Full name of the route
    """
    return {
        # A Division (IRT)
        '1': {
            'color': '#EE352E',  # Red
            'text_color': '#FFFFFF',
            'name': '1 Train'
        },
        '2': {
            'color': '#EE352E',  # Red
            'text_color': '#FFFFFF',
            'name': '2 Train'
        },
        '3': {
            'color': '#EE352E',  # Red
            'text_color': '#FFFFFF',
            'name': '3 Train'
        },
        '4': {
            'color': '#00933C',  # Green
            'text_color': '#FFFFFF',
            'name': '4 Train'
        },
        '5': {
            'color': '#00933C',  # Green
            'text_color': '#FFFFFF',
            'name': '5 Train'
        },
        '6': {
            'color': '#00933C',  # Green
            'text_color': '#FFFFFF',
            'name': '6 Train'
        },
        '7': {
            'color': '#B933AD',  # Purple
            'text_color': '#FFFFFF',
            'name': '7 Train'
        },
        'S': {
            'color': '#808183',  # Gray
            'text_color': '#FFFFFF',
            'name': 'Shuttle'
        },
        
        # B Division (BMT/IND)
        'A': {
            'color': '#0039A6',  # Blue
            'text_color': '#FFFFFF',
            'name': 'A Train'
        },
        'B': {
            'color': '#FF6319',  # Orange
            'text_color': '#FFFFFF',
            'name': 'B Train'
        },
        'C': {
            'color': '#0039A6',  # Blue
            'text_color': '#FFFFFF',
            'name': 'C Train'
        },
        'D': {
            'color': '#FF6319',  # Orange
            'text_color': '#FFFFFF',
            'name': 'D Train'
        },
        'E': {
            'color': '#0039A6',  # Blue
            'text_color': '#FFFFFF',
            'name': 'E Train'
        },
        'F': {
            'color': '#FF6319',  # Orange
            'text_color': '#FFFFFF',
            'name': 'F Train'
        },
        'G': {
            'color': '#6CBE45',  # Light Green
            'text_color': '#FFFFFF',
            'name': 'G Train'
        },
        'J': {
            'color': '#996633',  # Brown
            'text_color': '#FFFFFF',
            'name': 'J Train'
        },
        'L': {
            'color': '#A7A9AC',  # Gray
            'text_color': '#000000',
            'name': 'L Train'
        },
        'M': {
            'color': '#FF6319',  # Orange
            'text_color': '#FFFFFF',
            'name': 'M Train'
        },
        'N': {
            'color': '#FCCC0A',  # Yellow
            'text_color': '#000000',
            'name': 'N Train'
        },
        'Q': {
            'color': '#FCCC0A',  # Yellow
            'text_color': '#000000',
            'name': 'Q Train'
        },
        'R': {
            'color': '#FCCC0A',  # Yellow
            'text_color': '#000000',
            'name': 'R Train'
        },
        'W': {
            'color': '#FCCC0A',  # Yellow
            'text_color': '#000000',
            'name': 'W Train'
        },
        'Z': {
            'color': '#996633',  # Brown
            'text_color': '#FFFFFF',
            'name': 'Z Train'
        }
    } 