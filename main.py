#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fibonacci Market Cycle Trading System
Main entry point for command-line operations
"""

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime
import json

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
    """Main entry point for the Fibonacci Cycle Trading System"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Fibonacci Market Cycle Trading System')
    parser.add_argument('--web', action='store_true', help='Start web application')
    parser.add_argument('--scan', help='Scan a symbol or list of symbols (comma-separated)')
    parser.add_argument('--interval', default='daily', help='Timeframe interval (e.g., daily, 15min)')
    parser.add_argument('--lookback', type=int, default=5000, help='Number of bars to fetch')
    parser.add_argument('--exchange', default='NSE', help='Exchange to fetch data from')
    parser.add_argument('--file', help='Symbols file to scan')
    parser.add_argument('--output', help='Output directory for reports')
    parser.add_argument('--telegram', action='store_true', help='Send results to Telegram')
    parser.add_argument('--gpu', action='store_true', help='Use GPU acceleration if available')
    parser.add_argument('--workers', type=int, default=5, help='Number of worker threads for batch scanning')
    parser.add_argument('--backtest', help='Run backtest on a symbol')
    parser.add_argument('--days', type=int, default=90, help='Number of days for backtest')
    parser.add_argument('--strategy', default='fld_crossover', help='Strategy for backtest')
    args = parser.parse_args()

    # Setup output directory
    output_dir = args.output or './data/reports'
    os.makedirs(output_dir, exist_ok=True)

    # Import components
    try:
        from core.scanner import FibCycleScanner, ScanParameters
        from core.data_manager import DataManager
        from integration.export_engine import ExportEngine
    except ImportError as e:
        logger.error(f"Error importing core components: {e}")
        print(f"Error: {e}")
        print("Make sure you have installed all required dependencies.")
        sys.exit(1)

    # Initialize components
    data_manager = DataManager()
    scanner = FibCycleScanner(exchange=args.exchange, output_dir=output_dir)
    export_engine = ExportEngine()

    # Initialize Telegram reporter if requested
    telegram_reporter = None
    if args.telegram:
        try:
            from integration.telegram_bot import TelegramReporter
            
            # Get Telegram credentials from environment
            token = os.environ.get('TELEGRAM_BOT_TOKEN')
            chat_id = os.environ.get('TELEGRAM_CHAT_ID')
            
            if token and chat_id:
                telegram_reporter = TelegramReporter(token=token, chat_id=chat_id, scanner=scanner)
                logger.info("Telegram reporter initialized")
            else:
                logger.warning("Telegram credentials not found. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")
                print("Warning: Telegram credentials not found. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")
        except Exception as e:
            logger.error(f"Error initializing Telegram reporter: {e}")
            print(f"Warning: Could not initialize Telegram reporter: {e}")

    # Handle command line actions
    try:
        if args.web:
            # Start web application
            logger.info("Starting web application...")
            print("Starting web application...")
            
            try:
                import web.app
                web.app.app.run_server(debug=True)
            except ImportError:
                logger.error("Web application components not found.")
                print("Error: Web application components not found.")
                print("Make sure you have installed dash and dash-bootstrap-components packages.")
                sys.exit(1)
            
        elif args.backtest:
            # Run backtest on a symbol
            run_backtest(args, scanner, telegram_reporter, output_dir)
            
        elif args.scan:
            # Run scan on symbol(s)
            run_scan(args, scanner, data_manager, export_engine, telegram_reporter, output_dir)
            
        elif args.file:
            # Run scan on symbols from file
            run_file_scan(args, scanner, data_manager, export_engine, telegram_reporter, output_dir)
            
        else:
            # No specific command, show help
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        traceback.print_exc()
        print(f"Error: {e}")
        sys.exit(1)

def run_scan(args, scanner, data_manager, export_engine, telegram_reporter, output_dir):
    """Run scan for symbol(s)"""
    logger.info(f"Scanning {args.scan} on {args.interval} timeframe...")
    print(f"Scanning {args.scan} on {args.interval} timeframe...")
    
    # Create scan parameters
    from core.scanner import ScanParameters
    params = ScanParameters(
        lookback=args.lookback,
        use_gpu=args.gpu
    )
    
    if ',' in args.scan:
        # Multiple symbols
        symbols = [s.strip().upper() for s in args.scan.split(',') if s.strip()]
        
        # Run batch scan
        start_time = time.time()
        results = scanner.scan_batch(
            symbols=symbols,
            interval_name=args.interval,
            params=params,
            max_workers=args.workers
        )
        scan_time = time.time() - start_time
        
        # Export results
        if results:
            # Export to CSV and Excel
            csv_file = export_engine.export_to_csv(
                results, 
                os.path.join(output_dir, f"scan_{args.interval}_{len(results)}_results.csv")
            )
            excel_file = export_engine.export_to_excel(
                results,
                os.path.join(output_dir, f"scan_{args.interval}_{len(results)}_results.xlsx")
            )
            html_file = export_engine.generate_html_report(
                results,
                os.path.join(output_dir, f"scan_{args.interval}_{len(results)}_report.html")
            )
            
            # Print summary
            print(f"\nScan completed in {scan_time:.2f} seconds.")
            print(f"Found {len(results)} signals in {len(symbols)} symbols.")
            
            # Print top signals
            if results:
                print("\nTop Buy Signals:")
                buy_signals = [r for r in results if "Buy" in r.signal]
                for i, result in enumerate(sorted(buy_signals, key=lambda x: x.combined_strength, reverse=True)[:5], 1):
                    print(f"{i}. {result.symbol}: {result.signal} ({result.combined_strength:.2f})")
                
                print("\nTop Sell Signals:")
                sell_signals = [r for r in results if "Sell" in r.signal]
                for i, result in enumerate(sorted(sell_signals, key=lambda x: -x.combined_strength, reverse=True)[:5], 1):
                    print(f"{i}. {result.symbol}: {result.signal} ({result.combined_strength:.2f})")
            
            print(f"\nResults saved to:")
            print(f"- CSV: {csv_file}")
            print(f"- Excel: {excel_file}")
            print(f"- HTML Report: {html_file}")
            
            # Send to Telegram if requested
            if telegram_reporter:
                try:
                    # Format results for Telegram
                    buy_count = len([r for r in results if "Buy" in r.signal])
                    sell_count = len([r for r in results if "Sell" in r.signal])
                    
                    telegram_reporter.send_scan_report(
                        interval=args.interval,
                        total_symbols=len(symbols),
                        symbols_with_cycles=len(results),
                        buy_signals=buy_count,
                        sell_signals=sell_count
                    )
                    print("Scan report sent to Telegram.")
                except Exception as e:
                    logger.error(f"Error sending Telegram report: {e}")
                    print(f"Warning: Could not send Telegram report: {e}")
        else:
            print(f"No signals found in {len(symbols)} symbols.")
    else:
        # Single symbol
        result = scanner.analyze_symbol(args.scan.upper(), args.interval, params)
        
        if result:
            # Print results
# Print results
            print(f"\nAnalysis for {result.symbol} ({args.interval}):")
            print(f"Signal: {result.signal} ({result.confidence})")
            print(f"Strength: {result.combined_strength:.2f}")
            print(f"Cycles: {', '.join(str(c) for c in result.cycles)}")
            print(f"Last Price: {result.last_price:.2f}")
            print(f"Last Date: {result.last_date}")
            
            # Print guidance
            if hasattr(result, 'guidance') and result.guidance:
                guidance = result.guidance
                print("\nTrading Recommendation:")
                print(f"Action: {guidance['action']}")
                print(f"Entry Strategy: {guidance['entry_strategy']}")
                print(f"Exit Strategy: {guidance['exit_strategy']}")
                if guidance.get('stop_loss'):
                    print(f"Stop Loss: {guidance['stop_loss']:.2f}")
                if guidance.get('target'):
                    print(f"Target: {guidance['target']:.2f}")
                print(f"Position Size: {int(guidance['position_size'] * 100)}%")
                print(f"Timeframe: {guidance['timeframe']}")
            
            # Generate chart
            chart_file = scanner.generate_plot_image(
                result.symbol, 
                result.plot_data, 
                result.cycles, 
                result.cycle_states, 
                as_base64=False
            )
            
            if chart_file:
                print(f"\nChart saved to: {chart_file}")
            
            # Export to CSV for single symbol
            csv_file = export_engine.export_to_csv(
                [result],
                os.path.join(output_dir, f"{result.symbol}_{args.interval}_analysis.csv")
            )
            
            if csv_file:
                print(f"Analysis results saved to: {csv_file}")
            
            # Send to Telegram if requested
            if telegram_reporter:
                try:
                    telegram_reporter.send_message(
                        f"*{result.symbol} - {args.interval.upper()} Analysis*\n\n"
                        f"*Signal:* {result.signal}\n"
                        f"*Confidence:* {result.confidence}\n"
                        f"*Strength:* {result.combined_strength:.2f}\n"
                        f"*Cycles:* {', '.join(str(c) for c in result.cycles)}"
                    )
                    
                    # Try to send chart image
                    with open(chart_file, 'rb') as f:
                        telegram_reporter.send_image(f, f"{result.symbol} {args.interval} chart with FLDs")
                    
                    print("Analysis sent to Telegram.")
                except Exception as e:
                    logger.error(f"Error sending Telegram analysis: {e}")
                    print(f"Warning: Could not send Telegram analysis: {e}")
        else:
            print(f"No data available for {args.scan}")

def run_file_scan(args, scanner, data_manager, export_engine, telegram_reporter, output_dir):
    """Run scan on symbols from file"""
    if not os.path.exists(args.file):
        logger.error(f"Symbols file not found: {args.file}")
        print(f"Error: Symbols file not found: {args.file}")
        return
    
    # Load symbols from file
    symbols = data_manager.load_symbols_from_file(args.file)
    
    if not symbols:
        logger.warning(f"No symbols found in file: {args.file}")
        print(f"Warning: No symbols found in file: {args.file}")
        return
    
    logger.info(f"Loaded {len(symbols)} symbols from {args.file}")
    print(f"Loaded {len(symbols)} symbols from {args.file}")
    
    # Create scan parameters
    from core.scanner import ScanParameters
    params = ScanParameters(
        lookback=args.lookback,
        use_gpu=args.gpu
    )
    
    # Run batch scan
    start_time = time.time()
    print(f"Starting batch scan of {len(symbols)} symbols on {args.interval} timeframe...")
    
    results = scanner.scan_batch(
        symbols=symbols,
        interval_name=args.interval,
        params=params,
        max_workers=args.workers
    )
    
    scan_time = time.time() - start_time
    
    # Process results
    if results:
        # Export to CSV and Excel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        csv_file = export_engine.export_to_csv(
            results, 
            os.path.join(output_dir, f"filescan_{timestamp}_{args.interval}_{len(results)}_results.csv")
        )
        
        excel_file = export_engine.export_to_excel(
            results,
            os.path.join(output_dir, f"filescan_{timestamp}_{args.interval}_{len(results)}_results.xlsx")
        )
        
        html_file = export_engine.generate_html_report(
            results,
            os.path.join(output_dir, f"filescan_{timestamp}_{args.interval}_{len(results)}_report.html")
        )
        
        # Print summary
        print(f"\nScan completed in {scan_time:.2f} seconds.")
        print(f"Found {len(results)} signals in {len(symbols)} symbols.")
        
        # Print top signals
        if results:
            print("\nTop Buy Signals:")
            buy_signals = [r for r in results if "Buy" in r.signal]
            for i, result in enumerate(sorted(buy_signals, key=lambda x: x.combined_strength, reverse=True)[:5], 1):
                print(f"{i}. {result.symbol}: {result.signal} ({result.combined_strength:.2f})")
            
            print("\nTop Sell Signals:")
            sell_signals = [r for r in results if "Sell" in r.signal]
            for i, result in enumerate(sorted(sell_signals, key=lambda x: -x.combined_strength, reverse=True)[:5], 1):
                print(f"{i}. {result.symbol}: {result.signal} ({result.combined_strength:.2f})")
        
        print(f"\nResults saved to:")
        print(f"- CSV: {csv_file}")
        print(f"- Excel: {excel_file}")
        print(f"- HTML Report: {html_file}")
        
        # Send to Telegram if requested
        if telegram_reporter:
            try:
                # Format results for Telegram
                buy_count = len([r for r in results if "Buy" in r.signal])
                sell_count = len([r for r in results if "Sell" in r.signal])
                
                telegram_reporter.send_scan_report(
                    interval=args.interval,
                    total_symbols=len(symbols),
                    symbols_with_cycles=len(results),
                    buy_signals=buy_count,
                    sell_signals=sell_count
                )
                print("Scan report sent to Telegram.")
            except Exception as e:
                logger.error(f"Error sending Telegram report: {e}")
                print(f"Warning: Could not send Telegram report: {e}")
    else:
        print(f"No signals found in {len(symbols)} symbols.")

def run_backtest(args, scanner, telegram_reporter, output_dir):
    """Run backtest on a symbol"""
    logger.info(f"Running {args.days}-day backtest for {args.backtest} on {args.interval} timeframe...")
    print(f"Running {args.days}-day backtest for {args.backtest} on {args.interval} timeframe...")
    
    try:
        # Import backtesting components
        from analysis.backtest_engine import BacktestEngine
        from core.scanner import ScanParameters
        
        # Create parameters
        params = ScanParameters(
            lookback=max(5000, args.days * 2),
            use_gpu=args.gpu
        )
        
        # Fetch data
        data = scanner.fetch_data(args.backtest.upper(), args.interval, params.lookback)
        
        if data is None or len(data) < args.days:
            logger.warning(f"Insufficient data for {args.backtest} backtest")
            print(f"Error: Insufficient data for {args.backtest} backtest")
            return
        
        # Use only the specified number of days
        data = data.iloc[-args.days:]
        
        # Run backtest
        backtest = BacktestEngine(data, params)
        
        results = backtest.run_backtest(
            strategy_type=args.strategy,
            stop_loss_type="atr",
            take_profit_type="next_cycle",
            position_sizing="risk_based"
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
        
        # Trade breakdown
        if metrics.get('winning_trades') is not None and metrics.get('losing_trades') is not None:
            print(f"Winning Trades: {metrics['winning_trades']}")
            print(f"Losing Trades: {metrics['losing_trades']}")
        
        # Generate equity curve chart
        chart_file = os.path.join(output_dir, f"{args.backtest}_{args.interval}_{args.days}_equity.png")
        fig = backtest.plot_equity_curve()
        fig.savefig(chart_file, dpi=100)
        
        print(f"\nEquity curve saved to: {chart_file}")
        
        # Create detailed report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"{args.backtest}_{args.interval}_{args.days}_backtest_{timestamp}.json")
        
        # Save basic metrics to JSON
        with open(report_file, 'w') as f:
            # Extract trade data for saving
            trades_data = [
                {
                    'entry_date': str(t['entry_date']),
                    'exit_date': str(t['exit_date']),
                    'entry_price': t['entry_price'],
                    'exit_price': t['exit_price'],
                    'profit_pct': t['profit_pct'],
                    'type': t['type'],
                    'exit_reason': t['exit_reason']
                }
                for t in results['trades']
            ]
            
            json.dump({
                'symbol': args.backtest,
                'interval': args.interval,
                'days': args.days,
                'strategy': args.strategy,
                'metrics': metrics,
                'trades': trades_data,
                'timestamp': timestamp
            }, f, indent=4)
        
        print(f"Backtest report saved to: {report_file}")
        
        # Send to Telegram if requested
        if telegram_reporter:
            try:
                message = (
                    f"*Backtest Results: {args.backtest} ({args.days} days)*\n\n"
                    f"*Total Return:* {metrics['total_return']:.2%}\n"
                    f"*Win Rate:* {metrics['win_rate']:.2%}\n"
                    f"*Profit Factor:* {metrics['profit_factor']:.2f}\n"
                    f"*Max Drawdown:* {metrics['max_drawdown']:.2%}\n"
                    f"*Sharpe Ratio:* {metrics['sharpe_ratio']:.2f}\n"
                    f"*Total Trades:* {metrics['total_trades']}"
                )
                
                telegram_reporter.send_message(message)
                
                # Send equity curve
                with open(chart_file, 'rb') as f:
                    telegram_reporter.send_image(f, f"{args.backtest} {args.interval} {args.days}-day Backtest")
                
                print("Backtest results sent to Telegram.")
            except Exception as e:
                logger.error(f"Error sending Telegram backtest results: {e}")
                print(f"Warning: Could not send Telegram backtest results: {e}")
    
    except ImportError as e:
        logger.error(f"Error importing backtest components: {e}")
        print(f"Error: {e}")
        print("Make sure your installation includes the backtest components.")
    
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        traceback.print_exc()
        print(f"Error running backtest: {e}")

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