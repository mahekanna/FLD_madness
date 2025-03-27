```python
# main.py (continued)

def main():
    """Main entry point for Fibonacci Cycle System"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Fibonacci Cycle Trading System')
    parser.add_argument('--web', action='store_true', help='Start web application')
    parser.add_argument('--scan', help='Scan a symbol or list of symbols')
    parser.add_argument('--interval', default='daily', help='Timeframe interval (e.g., daily, 15min)')
    parser.add_argument('--backtest', help='Run backtest on a symbol')
    parser.add_argument('--days', type=int, default=90, help='Number of days for backtest')
    parser.add_argument('--config', default='config.json', help='Configuration file path')
    parser.add_argument('--gpu', action='store_true', help='Enable GPU acceleration')
    parser.add_argument('--output', help='Output directory for reports')
    parser.add_argument('--telegram', action='store_true', help='Enable Telegram notifications')
    args = parser.parse_args()

    # Load configuration
    from utils.config_manager import ConfigManager
    config_manager = ConfigManager(args.config)
    
    # Setup output directory
    output_dir = args.output or config_manager.get('general', 'report_dir')
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize performance monitor
    from utils.performance import PerformanceMonitor
    performance_monitor = PerformanceMonitor(os.path.join(output_dir, 'performance.log'))
    
    # Initialize scanner
    from core.scanner import FibCycleScanner
    use_gpu = args.gpu or config_manager.get('performance', 'use_gpu')
    scanner = FibCycleScanner(exchange=config_manager.get('general', 'default_exchange'), output_dir=output_dir)
    
    # Initialize Telegram bot if enabled
    telegram_bot = None
    if args.telegram or config_manager.get('notifications', 'telegram_enabled'):
        from integration.telegram_bot import EnhancedTelegramBot
        token = config_manager.get('notifications', 'telegram_token')
        chat_id = config_manager.get('notifications', 'telegram_chat_id')
        if token and chat_id:
            telegram_bot = EnhancedTelegramBot(token, chat_id, scanner)
            logger.info("Telegram bot initialized")
        else:
            logger.warning("Telegram bot not initialized: missing token or chat ID")
    
    # Handle command line actions
    if args.web:
        # Start web application
        logger.info("Starting web application...")
        from web.app import app
        app.run(debug=True)
        
    elif args.scan:
        # Run scan
        logger.info(f"Scanning {args.scan} on {args.interval} timeframe...")
        performance_monitor.start_timer("scan")
        
        if ',' in args.scan:
            # Multiple symbols
            symbols = [s.strip() for s in args.scan.split(',')]
            
            # Create scan parameters
            from core.models import ScanParameters
            params = ScanParameters(
                lookback=config_manager.get('general', 'default_lookback'),
                use_gpu=use_gpu
            )
            
            # Run batch scan
            results = scanner.scan_batch(
                symbols=symbols,
                interval_name=args.interval,
                params=params,
                max_workers=config_manager.get('performance', 'max_workers')
            )
            
            # Export results
            if results:
                from integration.export_engine import ExportEngine
                exporter = ExportEngine()
                csv_file = exporter.export_to_csv(results, os.path.join(output_dir, f"scan_{args.interval}_{len(results)}_results.csv"))
                
                # Print summary
                print(f"\nScan Results ({len(results)} signals found):")
                for i, result in enumerate(results[:10], 1):  # Show top 10
                    print(f"{i}. {result.symbol}: {result.signal} ({result.combined_strength:.2f})")
                
                if len(results) > 10:
                    print(f"... and {len(results) - 10} more (see {csv_file})")
                
                # Send to Telegram if enabled
                if telegram_bot:
                    buy_signals = [vars(r) for r in results if "Buy" in r.signal]
                    sell_signals = [vars(r) for r in results if "Sell" in r.signal]
                    recent_crossings = []
                    
                    for r in results:
                        for cycle, state in r.cycle_states.items():
                            if state.get('recent_crossover', False) or state.get('recent_crossunder', False):
                                recent_crossings.append({
                                    'symbol': r.symbol,
                                    'type': 'Bullish' if state.get('recent_crossover', False) else 'Bearish',
                                    'cycle': cycle,
                                    'bars_ago': 1  # Simplified
                                })
                    
                    telegram_bot.send_scan_report(args.interval, buy_signals, sell_signals, recent_crossings)
            else:
                print("No signals found")
        else:
            # Single symbol
            from core.models import ScanParameters
            params = ScanParameters(
                lookback=config_manager.get('general', 'default_lookback'),
                use_gpu=use_gpu
            )
            
            result = scanner.analyze_symbol(args.scan, args.interval, params)
            
            if result:
                # Print results
                print(f"\nAnalysis for {result.symbol} ({args.interval}):")
                print(f"Signal: {result.signal} ({result.confidence})")
                print(f"Strength: {result.combined_strength:.2f}")
                print(f"Cycles: {', '.join(str(c) for c in result.cycles)}")
                
                # Generate chart
                chart_file = scanner.generate_plot_image(
                    result.symbol, result.plot_data, result.cycles, result.cycle_states, 
                    as_base64=False
                )
                
                print(f"Chart saved to {chart_file}")
                
                # Send to Telegram if enabled
                if telegram_bot:
                    telegram_bot.send_analysis(result)
            else:
                print(f"No data available for {args.scan}")
        
        performance_monitor.stop_timer("scan", metadata={"symbols": args.scan})
        
    elif args.backtest:
        # Run backtest
        logger.info(f"Running {args.days}-day backtest for {args.backtest}...")
        performance_monitor.start_timer("backtest")
        
        # Fetch data
        from core.models import ScanParameters
        params = ScanParameters(
            lookback=max(5000, args.days * 2),
            use_gpu=use_gpu
        )
        
        data = scanner.fetch_data(args.backtest, args.interval, params.lookback)
        
        if data is not None and len(data) >= args.days:
            # Use only the specified number of days
            data = data.iloc[-args.days:]
            
            # Run backtest
            from analysis.backtest_engine import BacktestEngine
            backtest = BacktestEngine(data, params)
            
            results = backtest.run_backtest(
                strategy_type=config_manager.get('backtest', 'default_strategy'),
                stop_loss_type=config_manager.get('backtest', 'default_stop_loss'),
                take_profit_type=config_manager.get('backtest', 'default_take_profit'),
                position_sizing=config_manager.get('backtest', 'default_position_sizing')
            )
            
            # Print results
            metrics = results['metrics']
            print(f"\nBacktest Results for {args.backtest} ({args.days} days):")
            print(f"Total Return: {metrics['total_return']:.2%}")
            print(f"Win Rate: {metrics['win_rate']:.2%}")
            print(f"Profit Factor: {metrics['profit_factor']:.2f}")
            print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
            print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"Total Trades: {metrics['total_trades']}")
            
            # Generate equity curve chart
            chart_file = os.path.join(output_dir, f"{args.backtest}_{args.interval}_{args.days}_equity.png")
            fig = backtest.plot_equity_curve()
            fig.savefig(chart_file, dpi=100)
            
            print(f"Equity curve saved to {chart_file}")
            
            # Send to Telegram if enabled
            if telegram_bot:
                telegram_bot.send_backtest_result(args.backtest, args.interval, args.days, results, chart_file)
        else:
            print(f"Insufficient data for {args.backtest} backtest")
        
        performance_monitor.stop_timer("backtest", metadata={"symbol": args.backtest, "days": args.days})
        
    else:
        # No specific command, show help
        parser.print_help()
    
    # Clean up
    if telegram_bot:
        telegram_bot.stop_bot()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        traceback.print_exc()
        sys.exit(1)
```

### 7.2 Web Application Initialization

```python
# web/app.py

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
from io import StringIO
import time
import random
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Import core components
from core.scanner import FibCycleScanner
from core.models import ScanParameters
from utils.config_manager import ConfigManager
from utils.performance import PerformanceMonitor
from integration.telegram_bot import EnhancedTelegramBot
from integration.export_engine import ExportEngine

# Initialize components
config_manager = ConfigManager()
performance_monitor = PerformanceMonitor()

# Initialize the scanner
scanner = FibCycleScanner(
    exchange=config_manager.get('general', 'default_exchange'),
    output_dir=config_manager.get('general', 'report_dir')
)

# Get Telegram credentials from configuration
TELEGRAM_BOT_TOKEN = config_manager.get('notifications', 'telegram_token', '')
TELEGRAM_CHAT_ID = config_manager.get('notifications', 'telegram_chat_id', '')

# Initialize the reporter with proper error handling
telegram_reporter = None
if config_manager.get('notifications', 'telegram_enabled', False) and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    telegram_reporter = EnhancedTelegramBot(
        token=TELEGRAM_BOT_TOKEN, 
        chat_id=TELEGRAM_CHAT_ID,
        scanner=scanner
    )

# Symbol file path and global loaded symbols list
SYMBOLS_FILE_PATH = config_manager.get('general', 'symbols_file_path', './data/symbols/default_symbols.csv')
loaded_symbols = []

# Function to load symbols from a file
def load_symbols_from_file(file_path=SYMBOLS_FILE_PATH):
    """Load symbols from a file on disk."""
    global loaded_symbols
    
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Symbols file not found: {file_path}")
            return []
        
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.csv':
            # Parse CSV file
            df = pd.read_csv(file_path)
            
            # Look for symbol column
            symbol_cols = [col for col in df.columns if any(term in col.lower() 
                          for term in ['symbol', 'ticker', 'name', 'scrip'])]
            
            if symbol_cols:
                # Use the first matching column
                symbol_col = symbol_cols[0]
                symbols = df[symbol_col].dropna().astype(str).str.strip().str.upper().tolist()
            else:
                # Use first column if no match found
                symbols = df.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
        else:
            # For text files
            with open(file_path, 'r') as f:
                symbols = [s.strip().upper() for s in f.read().splitlines() if s.strip()]
        
        # Filter out any empty or invalid symbols
        symbols = [s for s in symbols if s and len(s) > 0]
        
        # Update global loaded symbols
        loaded_symbols = symbols
        
        logger.info(f"Loaded {len(symbols)} symbols from {file_path}")
        return symbols
        
    except Exception as e:
        logger.error(f"Error loading symbols file: {str(e)}")
        return []

# Function to initialize the application
def initialize_app():
    global loaded_symbols
    
    # Load symbols from file
    symbols = load_symbols_from_file()
    
    # Set loaded_symbols global variable
    loaded_symbols = symbols
    
    logger.info(f"Application initialized with {len(loaded_symbols)} symbols")

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True)

server = app.server  # Needed for deployment

# Initialize the application
initialize_app()

# Import page layouts
from web.layouts import (
    dashboard_layout, 
    symbol_analysis_layout, 
    batch_scan_layout, 
    reports_layout, 
    settings_layout,
    sidebar
)

# Import callbacks
from web.callbacks import register_callbacks

# Set main layout
app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    html.Div(id="page-content", style={"margin-left": "18rem", "padding": "2rem"}),
    # Store components for state management
    dcc.Store(id='scan-results-store', storage_type='memory'),
    dcc.Store(id='settings-store', storage_type='local', data={
        'default_exchange': config_manager.get('general', 'default_exchange'),
        'default_interval': config_manager.get('general', 'default_interval'),
        'default_lookback': config_manager.get('general', 'default_lookback'),
        'use_gpu': config_manager.get('performance', 'use_gpu'),
        'max_workers': config_manager.get('performance', 'max_workers'),
        'symbols_file_path': SYMBOLS_FILE_PATH
    }),
    # Intervals for background tasks
    dcc.Interval(id='refresh-interval', interval=60000, n_intervals=0)  # 1 minute refresh
])

# Register callbacks
register_callbacks(app, scanner, loaded_symbols, telegram_reporter)

# Callback to render page content based on URL
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def render_page_content(pathname):
    if pathname == '/':
        