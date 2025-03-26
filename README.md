# MTA Train Status Display

This project displays real-time status information for the 4, 5, and 6 trains at the 59th St/Lexington Ave station. It's designed to be displayed on a Raspberry Pi with an LED matrix, but can also be viewed in a web browser.

## Prerequisites

- Python 3.7 or higher

## Setup

1. Clone this repository
2. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   .\venv\Scripts\activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. Make sure your virtual environment is activated (you should see `(venv)` in your terminal prompt)
2. Start the Flask application:
   ```bash
   python app.py
   ```
3. Open your web browser and navigate to `http://localhost:5000`

## Project Structure

- `app.py`: Main Flask application
- `templates/index.html`: HTML template for displaying train status
- `requirements.txt`: Python dependencies
- `venv/`: Virtual environment directory (created during setup)

## Next Steps

1. Integrate with LED matrix display
2. Add mobile app for remote control
3. Implement real-time updates using WebSocket 