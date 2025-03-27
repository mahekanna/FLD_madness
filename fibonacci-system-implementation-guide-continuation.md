### 2.3 Batch Scan Implementation

```python
def run_batch_scan(symbols, interval, params, max_workers=5, update_callback=None):
    """
    Run a batch scan on multiple symbols
    
    Args:
        symbols: List of symbols to scan
        interval: Timeframe interval
        params: ScanParameters object
        max_workers: Number of parallel workers
        update_callback: Optional callback function for progress updates
        
    Returns:
        List of ScanResult objects
    """
    # Initialize results
    results = []
    total_symbols = len(symbols)
    
    # Process in batches to avoid rate limiting
    batch_size = 10
    batch_delay = 2  # seconds
    
    # Notify start
    if update_callback:
        update_callback(0, f"Starting scan of {total_symbols} symbols...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Process in batches
        for batch_idx in range(0, total_symbols, batch_size):
            # Get batch
            end_idx = min(batch_idx + batch_size, total_symbols)
            batch_symbols = symbols[batch_idx:end_idx]
            
            # Update progress
            if update_callback:
                progress = (batch_idx / total_symbols) * 100
                update_callback(
                    progress, 
                    f"Processing batch {batch_idx//batch_size + 1}/{(total_symbols + batch_size - 1)//batch_size}..."
                )
            
            # Submit batch to executor
            futures = {
                executor.submit(scanner.analyze_symbol, symbol, interval, params): symbol 
                for symbol in batch_symbols
            }
            
            # Process results
            batch_results = []
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                    if result is not None:
                        batch_results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
            
            # Add batch results to overall results
            results.extend(batch_results)
            
            # Add delay between batches to avoid rate limiting
            if end_idx < total_symbols:
                time.sleep(batch_delay)
                
            # Update progress with batch results
            if update_callback:
                progress = (end_idx / total_symbols) * 100
                update_callback(
                    progress, 
                    f"Processed {end_idx}/{total_symbols} symbols. Found {len(batch_results)} signals in this batch."
                )
    
    # Sort results by signal strength
    results.sort(key=lambda x: abs(x.combined_strength), reverse=True)
    
    # Final update
    if update_callback:
        update_callback(
            100, 
            f"Scan complete. Found {len(results)} signals from {total_symbols} symbols."
        )
    
    return results
```

### 2.4 Dashboard Components

```python
def create_dashboard_components(scan_results):
    """
    Create components for the dashboard
    
    Args:
        scan_results: Dict with scan results by timeframe
        
    Returns:
        Dict of dashboard components
    """
    # Extract key metrics
    metrics = calculate_dashboard_metrics(scan_results)
    
    # Create summary cards
    summary_cards = dbc.Row([
        # Market overview card
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Market Overview", className="card-title"),
                    html.P(f"Overall Market Bias: {metrics['market_bias']}", className="mb-2"),
                    html.P(f"Bullish Instruments: {metrics['bullish_count']} ({metrics['bullish_percent']}%)", 
                           className="text-success mb-1"),
                    html.P(f"Bearish Instruments: {metrics['bearish_count']} ({metrics['bearish_percent']}%)", 
                           className="text-danger mb-1"),
                    html.P(f"Neutral Instruments: {metrics['neutral_count']} ({metrics['neutral_percent']}%)", 
                           className="text-secondary mb-1"),
                    html.Div([
                        dbc.Progress(
                            [
                                dbc.Progress(value=metrics['bullish_percent'], color="success", bar=True),
                                dbc.Progress(value=metrics['bearish_percent'], color="danger", bar=True),
                            ],
                            multi=True,
                            style={"height": "20px"}
                        )
                    ], className="mt-2")
                ])
            ]),
            width=4
        ),
        
        # Top buy signals card
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Top Buy Signals", className="card-title"),
                    create_top_signals_table(metrics['top_buys'])
                ])
            ]),
            width=4
        ),
        
        # Top sell signals card
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Top Sell Signals", className="card-title"),
                    create_top_signals_table(metrics['top_sells'])
                ])
            ]),
            width=4
        ),
    ], className="mb-4")
    
    # Create recent crossings card
    crossings_card = dbc.Card([
        dbc.CardBody([
            html.H4("Recent FLD Crossings", className="card-title"),
            create_recent_crossings_table(metrics['recent_crossings'])
        ])
    ], className="mb-4")
    
    # Create timeframe summary tabs
    timeframe_tabs = dbc.Tabs([
        dbc.Tab(
            create_timeframe_summary(timeframe, results),
            label=timeframe.upper(),
            tab_id=f"tab-{timeframe}"
        ) for timeframe, results in scan_results.items() if results
    ], id="timeframe-tabs", active_tab="tab-daily", className="mb-4")
    
    return {
        "summary_cards": summary_cards,
        "crossings_card": crossings_card,
        "timeframe_tabs": timeframe_tabs
    }
```

### 2.5 Settings Page Implementation

```python
def create_settings_layout(current_settings):
    """
    Create the settings page layout
    
    Args:
        current_settings: Dictionary with current settings
        
    Returns:
        Dash layout for settings page
    """
    return html.Div([
        html.H1("Scanner Settings", className="mb-4"),
        
        # Default parameters card
        dbc.Card([
            dbc.CardBody([
                html.H4("Default Parameters", className="card-title"),
                dbc.Row([
                    # Default exchange
                    dbc.Col([
                        html.Label("Default Exchange"),
                        dbc.Input(
                            id="default-exchange-input", 
                            value=current_settings.get('default_exchange', 'NSE')
                        ),
                    ], width=4),
                    
                    # Default interval
                    dbc.Col([
                        html.Label("Default Interval"),
                        dbc.Select(
                            id="default-interval-input",
                            options=[
                                {"label": "Weekly", "value": "weekly"},
                                {"label": "Daily", "value": "daily"},
                                {"label": "4 Hour", "value": "4h"},
                                {"label": "1 Hour", "value": "1h"},
                                {"label": "15 Minute", "value": "15min"},
                                {"label": "5 Minute", "value": "5min"},
                            ],
                            value=current_settings.get('default_interval', 'daily')
                        ),
                    ], width=4),
                    
                    # Default lookback
                    dbc.Col([
                        html.Label("Default Lookback"),
                        dbc.Input(
                            id="default-lookback-input", 
                            type="number", 
                            value=current_settings.get('default_lookback', 5000)
                        ),
                    ], width=4),
                ], className="mb-3"),
                
                dbc.Row([
                    # Max workers
                    dbc.Col([
                        html.Label("Max Workers"),
                        dbc.Input(
                            id="max-workers-input", 
                            type="number", 
                            value=current_settings.get('max_workers', 5), 
                            min=1, 
                            max=20
                        ),
                    ], width=4),
                    
                    # GPU acceleration
                    dbc.Col([
                        html.Label("Hardware Acceleration"),
                        dbc.RadioItems(
                            id="hardware-acceleration",
                            options=[
                                {"label": "CPU Only", "value": "cpu"},
                                {"label": "GPU Acceleration (if available)", "value": "gpu"},
                                {"label": "Auto-detect", "value": "auto"},
                            ],
                            value=current_settings.get('hardware_acceleration', 'auto'),
                            inline=True
                        ),
                    ], width=4),
                    
                    # Auto-update interval
                    dbc.Col([
                        html.Label("Auto-update Interval (seconds)"),
                        dbc.Input(
                            id="auto-update-input", 
                            type="number", 
                            value=current_settings.get('auto_update_interval', 300), 
                            min=0, 
                            max=3600
                        ),
                    ], width=4),
                ], className="mb-3"),
                
                dbc.Button("Save General Settings", id="save-general-settings", color="primary"),
                html.Div(id="general-settings-status", className="mt-2"),
            ])
        ], className="mb-4"),
        
        # Cycle parameters card
        dbc.Card([
            dbc.CardBody([
                html.H4("Cycle Parameters", className="card-title"),
                dbc.Row([
                    # Standard Fibonacci cycles
                    dbc.Col([
                        html.Label("Standard Fibonacci Cycles"),
                        dbc.Input(
                            id="fib-cycles-input", 
                            value=", ".join(map(str, current_settings.get('fib_cycles', [20, 21, 34, 55, 89])))
                        ),
                        html.Small("Comma-separated list of cycle periods", className="text-muted"),
                    ], width=6),
                    
                    # Min/Max period range
                    dbc.Col([
                        html.Label("Min/Max Period Range"),
                        dbc.InputGroup([
                            dbc.Input(
                                id="min-period-input", 
                                type="number", 
                                value=current_settings.get('min_period', 10)
                            ),
                            dbc.InputGroupText("to"),
                            dbc.Input(
                                id="max-period-input", 
                                type="number", 
                                value=current_settings.get('max_period', 250)
                            ),
                        ]),
                        html.Small("Range of cycle periods to detect", className="text-muted"),
                    ], width=6),
                ], className="mb-3"),
                
                dbc.Row([
                    # Cycle detection method
                    dbc.Col([
                        html.Label("Cycle Detection Method"),
                        dbc.Select(
                            id="cycle-detection-method",
                            options=[
                                {"label": "FFT Analysis", "value": "fft"},
                                {"label": "Wavelet Analysis", "value": "wavelet"},
                                {"label": "Combined (FFT + Wavelet)", "value": "combined"},
                            ],
                            value=current_settings.get('cycle_detection_method', 'fft')
                        ),
                    ], width=6),
                    
                    # Signal threshold
                    dbc.Col([
                        html.Label("Signal Strength Threshold"),
                        dbc.Input(
                            id="signal-threshold-input", 
                            type="number", 
                            value=current_settings.get('signal_threshold', 1.0),
                            step=0.1
                        ),
                        html.Small("Minimum strength for valid signals", className="text-muted"),
                    ], width=6),
                ], className="mb-3"),
                
                dbc.Button("Update Cycle Parameters", id="update-cycles-button", color="primary"),
                html.Div(id="cycle-settings-status", className="mt-2"),
            ])
        ], className="mb-4"),
        
        # Notification settings card
        dbc.Card([
            dbc.CardBody([
                html.H4("Notification Settings", className="card-title"),
                dbc.Row([
                    # Telegram bot token
                    dbc.Col([
                        html.Label("Telegram Bot Token"),
                        dbc.Input(
                            id="telegram-token-input", 
                            type="password", 
                            value=current_settings.get('telegram_token', ''),
                            placeholder="Enter your bot token"
                        ),
                    ], width=6),
                    
                    # Telegram chat ID
                    dbc.Col([
                        html.Label("Telegram Chat ID"),
                        dbc.Input(
                            id="telegram-chatid-input", 
                            value=current_settings.get('telegram_chat_id', ''),
                            placeholder="Enter your chat ID"
                        ),
                    ], width=6),
                ], className="mb-3"),
                
                dbc.Row([
                    # Enable notifications
                    dbc.Col([
                        html.Label("Notification Options"),
                        dbc.Checklist(
                            id="notification-options",
                            options=[
                                {"label": "Send scan reports", "value": "scan_reports"},
                                {"label": "Alert on strong signals", "value": "strong_signals"},
                                {"label": "Alert on crossings", "value": "crossings"},
                                {"label": "Daily summary", "value": "daily_summary"},
                            ],
                            value=current_settings.get('notification_options', []),
                            inline=True
                        ),
                    ], width=8),
                    
                    # Test connection button
                    dbc.Col([
                        html.Br(),  # For alignment
                        dbc.Button("Test Connection", id="test-telegram-button", color="info"),
                    ], width=4),
                ], className="mb-3"),
                
                html.Div(id="telegram-test-result"),
                dbc.Button("Save Notification Settings", id="save-notification-button", color="primary", className="mt-2"),
            ])
        ], className="mb-4"),
        
        # Symbols file settings card
        dbc.Card([
            dbc.CardBody([
                html.H4("Symbols List Settings", className="card-title"),
                dbc.Row([
                    # Symbols file path
                    dbc.Col([
                        html.Label("Symbols File Path:"),
                        dbc.Input(
                            id="symbols-file-path", 
                            value=current_settings.get('symbols_file_path', './symbols.csv'),
                            placeholder="Path to symbols CSV or text file"
                        ),
                    ], width=9),
                    
                    # Update path button
                    dbc.Col([
                        html.Br(),  # For alignment
                        dbc.Button("Update Path", id="update-path-button", color="primary"),
                    ], width=3),
                ]),
                html.Div(id="update-path-status", className="mt-2"),