#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web application launcher for Fibonacci Cycle Trading System
"""

import os
import sys
import logging
import argparse
from pathlib import Path

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

def main():
    """Launch the Fibonacci Cycle Web Application"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Fibonacci Cycle Web Application')
    parser.add_argument('--port', type=int, default=8050, help='Port to run the application on')
    parser.add_argument('--host', default='127.0.0.1', help='Host to run the application on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--reload', action='store_true', help='Enable automatic reloading on code changes')
    args = parser.parse_args()
    
    # Add project root to path
    project_root = os.path.abspath(os.path.dirname(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Check if Google Drive path exists
    drive_path = "G:\\My Drive\\FLD-FIB-CYCLE"
    if not os.path.exists(drive_path):
        try:
            # Try to create the directory
            os.makedirs(drive_path, exist_ok=True)
            logger.info(f"Created Google Drive directory: {drive_path}")
        except Exception as e:
            logger.warning(f"Google Drive path not accessible: {e}")
            print(f"Warning: Google Drive path '{drive_path}' is not accessible.")
            print("The application will continue but may not be able to save data to Google Drive.")
    else:
        logger.info(f"Google Drive path found: {drive_path}")
    
    # Ensure other required directories exist
    required_dirs = [
        "./data",
        "./data/cache",
        "./data/symbols",
        "./data/reports",
        "./logs"
    ]
    
    for directory in required_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            except Exception as e:
                logger.error(f"Error creating directory {directory}: {e}")
    
    # Check if a default symbols file exists, if not create one
    symbols_file = "./data/symbols/default_symbols.csv"
    if not os.path.exists(symbols_file):
        try:
            with open(symbols_file, "w") as f:
                # Write header
                f.write("symbol\n")
                # Add some example symbols
                f.write("RELIANCE\n")
                f.write("TCS\n")
                f.write("HDFCBANK\n")
                f.write("INFY\n")
                f.write("ICICIBANK\n")
            logger.info(f"Created default symbols file: {symbols_file}")
        except Exception as e:
            logger.error(f"Error creating default symbols file: {e}")
    
    try:
        # Import the web application
        from web.app import app, server
        
        # Start the application
        logger.info(f"Starting web application on {args.host}:{args.port}")
        app.run_server(
            host=args.host,
            port=args.port,
            debug=args.debug,
            dev_tools_hot_reload=args.reload
        )
    
    except ImportError as e:
        logger.error(f"Error importing web application: {e}")
        print(f"Error: {e}")
        print("Make sure you have installed all required dependencies:")
        print("  pip install dash dash-bootstrap-components pandas numpy plotly tvdatafeed talib-binary scipy")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error starting web application: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()