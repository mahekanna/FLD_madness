import dash
from dash import dcc, html, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import json
import os
import base64
from datetime import datetime
import time
import logging
import sys

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import core components
from core.scanner import FibCycleScanner, ScanParameters
from core.data_manager import DataManager
from integration.telegram_bot import TelegramReporter
from integration.export_engine import ExportEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fib_scanner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import Google Drive integration
try:
    from integration.google_drive_integration import drive_storage
    DRIVE_AVAILABLE = os.path.exists(drive_storage.base_path)
    if DRIVE_AVAILABLE:
        logger.info(f"Google Drive storage available at {drive_storage.base_path}")
    else:
        logger.info("Google Drive storage not available")
except Exception as e:
    logger.warning(f"Could not import Google Drive integration: {e}")
    DRIVE_AVAILABLE = False

# Constants and paths setup
DEFAULT_EXCHANGE = "NSE"

# Check if Google Drive path is accessible
if DRIVE_AVAILABLE:
    # Use Google Drive for paths
    SYMBOLS_FILE_PATH = drive_storage.get_symbols_file_path()
    REPORTS_DIR = drive_storage.get_path("reports")
    LOGS_DIR = drive_storage.get_path("logs")
    CACHE_DIR = drive_storage.get_path("cache")
    logger.info(f"Using Google Drive storage at {drive_storage.base_path}")
else:
    # Fall back to local paths
    SYMBOLS_FILE_PATH = os.environ.get('SYMBOLS_FILE_PATH', './data/symbols/default_symbols.csv')
    REPORTS_DIR = './data/reports'
    LOGS_DIR = './logs'
    CACHE_DIR = './data/cache'
    logger.warning(f"Google Drive not accessible, using local storage")

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Initialize components
data_manager = DataManager(cache_dir=CACHE_DIR, max_age=86400)
scanner = FibCycleScanner(exchange=DEFAULT_EXCHANGE, output_dir=REPORTS_DIR)
export_engine = ExportEngine()

# Initialize Telegram reporter if credentials are available
telegram_reporter = None
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    try:
        telegram_reporter = TelegramReporter(
            token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID,
            scanner=scanner
        )
        logger.info("Telegram reporter initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Telegram reporter: {e}")

# Load symbols
loaded_symbols = []

def load_symbols_from_file(file_path=SYMBOLS_FILE_PATH):
    """Load symbols from a file"""
    global loaded_symbols
    loaded_symbols = data_manager.load_symbols_from_file(file_path)
    return loaded_symbols

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

server = app.server  # For deployment

# Load symbols on startup
load_symbols_from_file()

# Define page layouts
from .layouts import (
    sidebar,
    dashboard_layout,
    symbol_analysis_layout,
    batch_scan_layout,
    reports_layout,
    settings_layout
)

# Main layout
app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    html.Div(id="page-content", style={"margin-left": "18rem", "padding": "2rem"}),
    
    # Store components for state management
    dcc.Store(id='scan-results-store', storage_type='memory'),
    dcc.Store(id='settings-store', storage_type='local', data={
        'default_exchange': DEFAULT_EXCHANGE,
        'default_interval': 'daily',
        'default_lookback': 5000,
        'use_gpu': False,
        'max_workers': 5,
        'symbols_file_path': SYMBOLS_FILE_PATH,
        'drive_available': DRIVE_AVAILABLE,
        'drive_path': drive_storage.base_path if DRIVE_AVAILABLE else ''
    }),
    
    # Intervals for background tasks
    dcc.Interval(id='refresh-interval', interval=60000, n_intervals=0)  # 1 minute refresh
])

# Import callbacks
from .callbacks import register_callbacks

# Register all callbacks
register_callbacks(
    app=app,
    scanner=scanner,
    data_manager=data_manager,
    telegram_reporter=telegram_reporter,
    export_engine=export_engine,
    loaded_symbols=loaded_symbols
)

# Callback to render page content based on URL
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def render_page_content(pathname):
    if pathname == '/':
        return dashboard_layout
    elif pathname == '/symbol':
        return symbol_analysis_layout
    elif pathname == '/batch':
        return batch_scan_layout
    elif pathname == '/reports':
        return reports_layout
    elif pathname == '/settings':
        return settings_layout
    else:
        # If the user tries to navigate to a non-existent page
        return html.Div([
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognized..."),
        ])

# Shutdown handler to clean up the Telegram bot
@server.before_request
def before_request():
    # Register shutdown handler if not already done
    if not hasattr(server, 'bot_shutdown_registered'):
        server.bot_shutdown_registered = True
        
        @server.teardown_appcontext
        def shutdown_bot(exception=None):
            if telegram_reporter:
                telegram_reporter.stop_bot()
                logger.info("Telegram bot stopped during app shutdown")

if __name__ == '__main__':
    app.run_server(debug=True)