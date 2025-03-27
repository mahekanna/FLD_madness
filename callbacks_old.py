"""
Callback functions for the Fibonacci Cycle Web Application
"""
import os
import io
import time
import json
import base64
import logging
from datetime import datetime

import dash
from dash import callback, Input, Output, State, html, no_update, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Setup logger
logger = logging.getLogger(__name__)

#========================================================
# Helper Functions for UI Components
#========================================================

def create_cycle_state_item(cycle, state):
    """
    Create a display item for a cycle state
    
    Args:
        cycle: Cycle length
        state: Cycle state dictionary
        
    Returns:
        Dash component
    """
    direction = "Bullish" if state["bullish"] else "Bearish"
    direction_color = "success" if state["bullish"] else "danger"
    
    # Recent crossing badge
    crossing_badge = None
    if state.get("recent_crossover", False):
        crossing_badge = dbc.Badge("Recent bullish crossing", color="success", className="ms-2")
    elif state.get("recent_crossunder", False):
        crossing_badge = dbc.Badge("Recent bearish crossing", color="danger", className="ms-2")
    
    return html.Div([
        html.P([
            html.Strong(f"Cycle {cycle}: "),
            html.Span(direction, className=f"text-{direction_color}"),
            crossing_badge
        ]),
        html.P([
            html.Strong("Power: "),
            html.Span(f"{state['power']:.2f}")
        ], className="ms-3"),
        html.P([
            html.Strong("FLD Value: "),
            html.Span(f"{state['fld_value']:.2f}")
        ], className="ms-3"),
        html.Hr()
    ])

def create_interactive_chart(result):
    """
    Create an interactive chart for a symbol analysis
    
    Args:
        result: Analysis result object
        
    Returns:
        Dash Graph component
    """
    # Extract plot data
    plot_data = result.plot_data
    
    # Create figure with subplots
    fig = make_subplots(
        rows=2, 
        cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        specs=[
            [{"type": "candlestick"}],
            [{"type": "scatter"}]
        ]
    )
    
    # Add price candlesticks
    fig.add_trace(
        go.Candlestick(
            x=plot_data['dates'],
            open=plot_data['open'],
            high=plot_data['high'],
            low=plot_data['low'],
            close=plot_data['close'],
            name=result.symbol,
            increasing_line_color='#26a69a', 
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1
    )
    
    # Add FLDs for each cycle
    for cycle, cycle_data in plot_data['cycles'].items():
        fig.add_trace(
            go.Scatter(
                x=plot_data['dates'],
                y=cycle_data['fld'],
                name=f"FLD {cycle}",
                line=dict(color=cycle_data['color'], width=1.5, dash='dot'),
                hovertemplate=f"FLD {cycle}: %{{y:.2f}}<extra></extra>"
            ),
            row=1, col=1
        )
        
        # Add cycle wave if available
        if 'wave' in cycle_data:
            # Take the correct number of dates for the wave
            wave_dates = plot_data['dates'][-len(cycle_data['wave']):]
            
            fig.add_trace(
                go.Scatter(
                    x=wave_dates,
                    y=cycle_data['wave'],
                    name=f"Cycle {cycle}",
                    line=dict(color=cycle_data['color'], width=1, dash='dash'),
                    opacity=0.5,
                    hovertemplate=f"Cycle {cycle}: %{{y:.2f}}<extra></extra>"
                ),
                row=1, col=1
            )
    
    # Add crossings as markers
    for crossing in plot_data.get('crossings', []):
        marker_color = 'green' if crossing['type'] == 'bullish' else 'red'
        marker_symbol = 'triangle-up' if crossing['type'] == 'bullish' else 'triangle-down'
        
        fig.add_trace(
            go.Scatter(
                x=[crossing['date']],
                y=[crossing['price']],
                mode='markers',
                marker=dict(
                    color=marker_color,
                    size=12,
                    symbol=marker_symbol,
                    line=dict(width=1, color='black')
                ),
                name=f"{crossing['type'].title()} {crossing['cycle']}",
                hovertemplate=f"{crossing['type'].title()} {crossing['cycle']}<br>Price: %{{y:.2f}}<br>Date: %{{x}}<extra></extra>"
            ),
            row=1, col=1
        )
    
    # Add volume in bottom panel
    if 'volume' in plot_data and len(plot_data['volume']) > 0:
        # Color volume bars based on price movement
        colors = ['red' if plot_data['close'][i] < plot_data['open'][i] else 'green' 
                 for i in range(len(plot_data['close']))]
        
        fig.add_trace(
            go.Bar(
                x=plot_data['dates'],
                y=plot_data['volume'],
                marker_color=colors,
                name='Volume',
                opacity=0.7,
                hovertemplate="Volume: %{{y:,.0f}}<extra></extra>"
            ),
            row=2, col=1
        )
    
    # Update layout
    fig.update_layout(
        title=f"{result.symbol} - {result.interval.upper()} Chart with FLDs",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=600,
        template="plotly_white",
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # Add range selector
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1d", step="day", stepmode="backward"),
                dict(count=7, label="1w", step="day", stepmode="backward"),
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(step="all")
            ])
        ),
        row=2, col=1
    )
    
    # Enable zoom tools
    fig.update_layout(
        dragmode='zoom',
        hovermode='closest',
        hoverdistance=100,
        spikedistance=1000
    )
    
    # Add spikes on hover for price tracking
    fig.update_xaxes(showspikes=True, spikemode='across', spikesnap='cursor', spikedash='dot')
    fig.update_yaxes(showspikes=True, spikemode='across', spikesnap='cursor', spikedash='dot')
    
    return dcc.Graph(
        figure=fig,
        config={
            'displayModeBar': True,
            'scrollZoom': True
        }
    )

def create_symbol_analysis_layout(result):
    """
    Create layout for symbol analysis results
    
    Args:
        result: Analysis result object
        
    Returns:
        Dash layout
    """
    # Determine signal color
    signal_color = "success" if "Buy" in result.signal else "danger" if "Sell" in result.signal else "secondary"
    
    # Create layout
    return html.Div([
        # Signal header
        dbc.Alert(
            [
                html.H3([
                    html.Span(f"{result.symbol} - {result.interval.upper()}: ", className="me-2"),
                    html.Span(result.signal, className=f"text-{signal_color}"),
                    html.Span(f" ({result.confidence})", className="ms-2 small")
                ], className="mb-0"),
                html.P(f"Last Price: {result.last_price} | Last Updated: {result.last_date}", className="mb-0 small"),
            ],
            color=signal_color,
            className="mb-4"
        ),
        
        # Main content
        dbc.Row([
            # Chart column
            dbc.Col([
                dbc.Card(
                    dbc.CardBody([
                        create_interactive_chart(result)
                    ])
                )
            ], width=8),
            
            # Analysis details column
            dbc.Col([
                # Signal details card
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Signal Details", className="card-title"),
                        html.P([
                            html.Strong("Signal: "),
                            html.Span(result.signal, className=f"text-{signal_color}")
                        ]),
                        html.P([
                            html.Strong("Confidence: "),
                            html.Span(result.confidence)
                        ]),
                        html.P([
                            html.Strong("Signal Strength: "),
                            html.Span(f"{result.combined_strength:.2f}")
                        ]),
                        html.P([
                            html.Strong("Cycles: "),
                            html.Span(", ".join(str(c) for c in result.cycles))
                        ]),
                    ]),
                    className="mb-3"
                ),
                
                # Cycle states card
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Cycle States", className="card-title"),
                        *[create_cycle_state_item(cycle, state) for cycle, state in result.cycle_states.items()]
                    ]),
                    className="mb-3"
                ),
                
                # Trading recommendation card
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Trading Recommendation", className="card-title"),
                        html.P([
                            html.Strong("Action: "),
                            html.Span(result.guidance["action"], className=f"text-{'success' if result.guidance['action'] == 'Buy' else 'danger' if result.guidance['action'] == 'Sell' else 'secondary'}")
                        ]),
                        html.P([
                            html.Strong("Entry Strategy: "),
                            html.Span(result.guidance["entry_strategy"])
                        ]),
                        html.P([
                            html.Strong("Exit Strategy: "),
                            html.Span(result.guidance["exit_strategy"])
                        ]),
                        html.H6("Risk Management:", className="mt-3 mb-2"),
                        html.Ul([
                            html.Li([
                                html.Strong("Stop Loss: "),
                                html.Span(f"{result.guidance['stop_loss']:.2f}" if result.guidance['stop_loss'] else "N/A")
                            ]),
                            html.Li([
                                html.Strong("Target: "),
                                html.Span(f"{result.guidance['target']:.2f}" if result.guidance['target'] else "N/A")
                            ]),
                            html.Li([
                                html.Strong("Position Size: "),
                                html.Span(f"{int(result.guidance['position_size'] * 100)}%")
                            ]),
                            html.Li([
                                html.Strong("Timeframe: "),
                                html.Span(result.guidance["timeframe"])
                            ])
                        ])
                    ])
                )
            ], width=4)
        ]),
        
        # Export button
        html.Div([
            dbc.Button("Export Analysis", id="export-analysis-button", color="success", className="mt-3")
        ], className="text-end"),
        
        # Download component
        dcc.Download(id="download-analysis")
    ])

def create_signals_table(results, signal_type):
    """
    Create a table of scan results
    
    Args:
        results: List of scan results
        signal_type: Signal type ("buy", "sell", or "all")
        
    Returns:
        Dash DataTable
    """
    # Create table header
    header = html.Thead(html.Tr([
        html.Th("Symbol"),
        html.Th("Signal"),
        html.Th("Confidence"),
        html.Th("Strength"),
        html.Th("Cycles"),
        html.Th("Actions")
    ]))
    
    # Create table rows
    rows = []
    for result in results:
        # Determine row color
        row_class = "table-success" if "Buy" in result.signal else "table-danger" if "Sell" in result.signal else ""
        
        rows.append(html.Tr([
            html.Td(result.symbol),
            html.Td(result.signal),
            html.Td(result.confidence),
            html.Td(f"{result.combined_strength:.2f}"),
            html.Td(", ".join(str(c) for c in result.cycles)),
            html.Td(dbc.Button("View", href=f"/symbol?symbol={result.symbol}&interval={result.interval}", color="primary", size="sm"))
        ], className=row_class))
    
    # Create table body
    body = html.Tbody(rows)
    
    # Create table
    return dbc.Table([header, body], bordered=True, hover=True, responsive=True, striped=True)

def create_batch_scan_results_layout(results):
    """
    Create layout for batch scan results
    
    Args:
        results: List of scan results
        
    Returns:
        Dash layout
    """
    # Count signal types
    buy_signals = [r for r in results if "Buy" in r.signal]
    sell_signals = [r for r in results if "Sell" in r.signal]
    
    # Create summary
    summary = dbc.Card(
        dbc.CardBody([
            html.H4("Scan Summary", className="card-title mb-3"),
            dbc.Row([
                dbc.Col([
                    html.H5("Total Signals", className="text-center"),
                    html.P(len(results), className="text-center h3")
                ], width=4),
                dbc.Col([
                    html.H5("Buy Signals", className="text-center text-success"),
                    html.P(len(buy_signals), className="text-center h3 text-success")
                ], width=4),
                dbc.Col([
                    html.H5("Sell Signals", className="text-center text-danger"),
                    html.P(len(sell_signals), className="text-center h3 text-danger")
                ], width=4),
            ]),
            html.P(f"Scan completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", className="text-muted small text-end mt-3 mb-0")
        ]),
        className="mb-4"
    )
    
    # Create tabs for buy and sell signals
    signal_tabs = dbc.Tabs([
        # Buy signals tab
        dbc.Tab(
            create_signals_table(buy_signals, "buy"),
            label=f"Buy Signals ({len(buy_signals)})",
            tab_id="buy-signals-tab"
        ),
        
        # Sell signals tab
        dbc.Tab(
            create_signals_table(sell_signals, "sell"),
            label=f"Sell Signals ({len(sell_signals)})",
            tab_id="sell-signals-tab"
        ),
        
        # All signals tab
        dbc.Tab(
            create_signals_table(results, "all"),
            label=f"All Signals ({len(results)})",
            tab_id="all-signals-tab"
        )
    ], id="signals-tabs", active_tab="all-signals-tab")
    
    # Create layout
    layout = html.Div([
        summary,
        signal_tabs,
        html.Div([
            dbc.Button(
                [html.I(className="fas fa-file-csv me-2"), "Export to CSV"], 
                id="export-csv-button", 
                color="success", 
                className="me-2"
            ),
            dbc.Button(
                [html.I(className="fas fa-file-excel me-2"), "Export to Excel"], 
                id="export-excel-button", 
                color="success", 
                className="me-2"
            ),
            dbc.Button(
                [html.I(className="fas fa-chart-bar me-2"), "Generate Report"], 
                id="generate-report-button", 
                color="info"
            ),
        ], className="text-end mt-3"),
        dcc.Download(id="download-csv"),
        dcc.Download(id="download-excel"),
        dcc.Download(id="download-report")
    ])
    
    return layout

#========================================================
# Callback Registration Function
#========================================================

def register_callbacks(app, scanner, loaded_symbols, telegram_reporter=None):
    """
    Register all callback functions with the Dash app
    
    Args:
        app: Dash application
        scanner: FibCycleScanner instance
        loaded_symbols: List of loaded symbols
        telegram_reporter: TelegramReporter instance (optional)
    """
    # Import performance monitor
    from utils.performance import performance_monitor
    
    #========================================================
    # Symbol Analysis Callbacks
    #========================================================
    
    @app.callback(
        [
            Output("analysis-results", "children"),
            Output("analysis-loading", "children"),
            Output("analysis-data-store", "data")
        ],
        Input("analyze-button", "n_clicks"),
        [
            State("symbol-input", "value"),
            State("interval-select", "value")
        ],
        prevent_initial_call=True
    )
    def analyze_symbol(n_clicks, symbol, interval):
        """
        Analyze a single symbol when the analyze button is clicked
        """
        if not n_clicks or not symbol:
            return no_update, no_update, no_update
        
        try:
            # Start performance timer
            performance_monitor.start_timer("symbol_analysis", {
                "symbol": symbol,
                "interval": interval
            })
            
            # Clean up symbol input
            symbol = symbol.strip().upper()
            
            # Create scan parameters
            from core.scanner import ScanParameters
            params = ScanParameters()
            
            # Run analysis
            result = scanner.analyze_symbol(symbol, interval, params)
            
            if result is None:
                return (
                    dbc.Alert(f"No data available for {symbol}", color="warning"),
                    "",
                    None
                )
            
            # Store data for export or further processing
            analysis_data = {
                "symbol": result.symbol,
                "interval": result.interval,
                "signal": result.signal,
                "confidence": result.confidence,
                "strength": result.combined_strength,
                "cycles": result.cycles,
                "last_price": result.last_price,
                "last_date": result.last_date,
                "timestamp": datetime.now().isoformat()
            }
            
            # Create result layout
            layout = create_symbol_analysis_layout(result)
            
            # Stop performance timer
            performance_monitor.stop_timer("symbol_analysis", True, {
                "has_result": True
            })
            
            return layout, "", analysis_data
            
        except Exception as e:
            logger.error(f"Error analyzing symbol: {e}", exc_info=True)
            
            # Stop performance timer with error
            if "symbol_analysis" in performance_monitor.timers:
                performance_monitor.stop_timer("symbol_analysis", False, {
                    "error": str(e)
                })
            
            return (
                dbc.Alert(f"Error analyzing {symbol}: {str(e)}", color="danger"),
                "",
                None
            )
    
    @app.callback(
        Output("download-analysis", "data"),
        Input("export-analysis-button", "n_clicks"),
        State("analysis-data-store", "data"),
        prevent_initial_call=True
    )
    def export_analysis(n_clicks, analysis_data):
        """
        Export analysis data when export button is clicked
        """
        if not n_clicks or not analysis_data:
            return no_update
        
        try:
            # Format data for CSV
            csv_data = io.StringIO()
            csv_data.write(f"Symbol,{analysis_data['symbol']}\n")
            csv_data.write(f"Interval,{analysis_data['interval']}\n")
            csv_data.write(f"Signal,{analysis_data['signal']}\n")
            csv_data.write(f"Confidence,{analysis_data['confidence']}\n")
            csv_data.write(f"Strength,{analysis_data['strength']}\n")
            csv_data.write(f"Cycles,{','.join(str(c) for c in analysis_data['cycles'])}\n")
            csv_data.write(f"Last Price,{analysis_data['last_price']}\n")
            csv_data.write(f"Last Date,{analysis_data['last_date']}\n")
            csv_data.write(f"Analysis Time,{analysis_data['timestamp']}\n")
            
            # Return download data
            return {
                "content": csv_data.getvalue(),
                "filename": f"{analysis_data['symbol']}_{analysis_data['interval']}_analysis.csv",
                "type": "text/csv"
            }
            
        except Exception as e:
            logger.error(f"Error exporting analysis: {e}")
            return no_update
    
    #========================================================
    # Batch Scan Callbacks
    #========================================================
    
    @app.callback(
        Output("symbols-source-container", "children"),
        Input("symbols-source", "value")
    )
    def update_symbols_source_ui(source_value):
        """
        Update UI based on selected symbols source
        """
        if source_value == "default":
            return html.Div([
                html.P(f"Using default symbols list: {len(loaded_symbols)} symbols", className="text-muted"),
                html.P("Configure default symbols list in Settings", className="text-muted small"),
            ])
        
        elif source_value == "custom":
            return html.Div([
                html.Label("Enter symbols (comma separated)"),
                dbc.Textarea(id="custom-symbols-input", placeholder="AAPL, MSFT, GOOG, ...", rows=3, className="mb-2"),
                html.P("Or upload a file", className="mb-1"),
                dcc.Upload(
                    id="upload-symbols-file",
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select a File')
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px 0'
                    }
                ),
            ])
        
        elif source_value == "index":
            return html.Div([
                html.Label("Select Market Index"),
                dbc.Select(
                    id="market-index-select",
                    options=[
                        {"label": "NIFTY 50", "value": "NIFTY50"},
                        {"label": "NIFTY Bank", "value": "BANKNIFTY"},
                        {"label": "NIFTY IT", "value": "NIFTYIT"},
                        {"label": "NIFTY Pharma", "value": "NIFTYPHARMA"},
                        {"label": "NIFTY Auto", "value": "NIFTYAUTO"},
                    ],
                    value="NIFTY50",
                    className="mb-2",
                ),
                html.P("Uses index components for scanning", className="text-muted small"),
            ])
        
        return html.Div()
    
    @app.callback(
        [
            Output("batch-scan-results", "children"),
            Output("batch-scan-loading", "children"),
            Output("scan-progress-container", "style"),
            Output("scan-progress", "value"),
            Output("scan-status", "children"),
            Output("batch-results-store", "data"),
            Output("export-csv-button", "disabled"),
            Output("export-excel-button", "disabled"),
            Output("generate-report-button", "disabled"),
        ],
        Input("start-scan-button", "n_clicks"),
        [
            State("symbols-source", "value"),
            State("custom-symbols-input", "value"),
            State("market-index-select", "value"),
            State("batch-interval-select", "value"),
            State("scan-filters", "value"),
        ],
        prevent_initial_call=True
    )
    def run_batch_scan(n_clicks, source_type, custom_symbols, market_index, interval, filters):
        """
        Run a batch scan on multiple symbols
        """
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        try:
            # Get symbols based on source type
            symbols = []
            
            if source_type == "default":
                symbols = loaded_symbols
            
            elif source_type == "custom" and custom_symbols:
                symbols = [s.strip().upper() for s in custom_symbols.split(',') if s.strip()]
            
            elif source_type == "index":
                # In a real implementation, these would be fetched from a data source
                # Here we use predefined lists as examples
                if market_index == "NIFTY50":
                    symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "KOTAKBANK", "LT", "AXISBANK"]
                elif market_index == "BANKNIFTY":
                    symbols = ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN", "INDUSINDBK", "FEDERALBNK", "BANDHANBNK", "AUBANK", "PNB"]
                else:
                    symbols = loaded_symbols[:10]  # Use first 10 symbols as fallback
            
            if not symbols:
                return (
                    dbc.Alert("No symbols selected for scanning", color="warning"),
                    "",
                    {"display": "none"},
                    0,
                    "",
                    None,
                    True,
                    True,
                    True
                )
            
            # Start performance timer
            performance_monitor.start_timer("batch_scan", {
                "num_symbols": len(symbols),
                "interval": interval,
                "filters": filters
            })
            
            # Show progress
            progress_style = {"display": "block"}
            progress_value = 5
            status_text = f"Preparing to scan {len(symbols)} symbols..."
            
            # Create scan parameters
            from core.scanner import ScanParameters
            params = ScanParameters(
                use_gpu="use_gpu" in filters
            )
            
            # Run batch scan
            # In a real implementation, this would update progress incrementally
            results = scanner.scan_batch(
                symbols=symbols,
                interval_name=interval,
                params=params,
                max_workers=5
            )
            
            # Apply filters if specified
            if filters:
                if "cycle_20_21" in filters:
                    results = [r for r in results if any(c in (20, 21) for c in r.cycles)]
                
                if "cycle_34" in filters:
                    results = [r for r in results if 34 in r.cycles]
                
                if "recent_crossing" in filters:
                    results = [r for r in results if any(
                        state.get('recent_crossover', False) or state.get('recent_crossunder', False)
                        for state in r.cycle_states.values()
                    )]
            
            # Store results
            if results:
                # Sort by strength
                results.sort(key=lambda x: abs(x.combined_strength), reverse=True)
                
                # Prepare for storage
                results_data = []
                for r in results:
                    results_data.append({
                        "symbol": r.symbol,
                        "interval": r.interval,
                        "signal": r.signal,
                        "confidence": r.confidence,
                        "strength": r.combined_strength,
                        "cycles": r.cycles,
                        "has_key_cycles": r.has_key_cycles
                    })
                
                # Create layout
                layout = create_batch_scan_results_layout(results)
                
                # Stop performance timer
                performance_monitor.stop_timer("batch_scan", True, {
                    "symbols_processed": len(symbols),
                    "signals_found": len(results)
                })
                
                return (
                    layout,
                    "",
                    {"display": "none"},
                    100,
                    f"Scan completed. Found {len(results)} signals from {len(symbols)} symbols.",
                    results_data,
                    False,
                    False,
                    False
                )
            else:
                # No results found
                return (
                    dbc.Alert(f"No signals found in {len(symbols)} symbols", color="warning"),
                    "",
                    {"display": "none"},
                    100,
                    f"Scan completed. No signals found in {len(symbols)} symbols.",
                    [],
                    True,
                    True,
                    True
                )
        
        except Exception as e:
            logger.error(f"Error running batch scan: {e}", exc_info=True)
            
            # Stop performance timer with error
            if "batch_scan" in performance_monitor.timers:
                performance_monitor.stop_timer("batch_scan", False, {
                    "error": str(e)
                })
            
            return (
                dbc.Alert(f"Error running scan: {str(e)}", color="danger"),
                "",
                {"display": "none"},
                0,
                f"Error: {str(e)}",
                None,
                True,
                True,
                True
            )
    
   
    @app.callback(
            Output("download-csv", "data"),
            Input("export-csv-button", "n_clicks"),
            State("batch-results-store", "data"),
            prevent_initial_call=True
        )
    def export_results_to_csv(n_clicks, results_data):
        """
        Export batch scan results to CSV
        """
        if not n_clicks or not results_data:
            return no_update
        
        try:
            # Create DataFrame from results
            df = pd.DataFrame(results_data)
            
            # Convert cycles lists to strings
            df['cycles'] = df['cycles'].apply(lambda x: ', '.join(map(str, x)))
            
            # Convert to CSV
            csv_string = df.to_csv(index=False)
            
            # Create timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            return {
                "content": csv_string,
                "filename": f"fibonacci_scan_{timestamp}.csv",
                "type": "text/csv"
            }
        
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return no_update
    
    @app.callback(
        Output("download-excel", "data"),
        Input("export-excel-button", "n_clicks"),
        State("batch-results-store", "data"),
        prevent_initial_call=True
    )
    def export_results_to_excel(n_clicks, results_data):
        """
        Export batch scan results to Excel
        """
        if not n_clicks or not results_data:
            return no_update
        
        try:
            # Create DataFrame from results
            df = pd.DataFrame(results_data)
            
            # Convert cycles lists to strings
            df['cycles'] = df['cycles'].apply(lambda x: ', '.join(map(str, x)))
            
            # Create timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name="Scan Results", index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets["Scan Results"]
                
                # Define formats
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'bg_color': '#D7E4BC',
                    'border': 1
                })
                
                # Apply header format
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Auto-fit columns
                for i, col in enumerate(df.columns):
                    max_len = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, max_len)
            
            # Reset buffer position
            output.seek(0)
            
            return {
                "content": output.getvalue(),
                "filename": f"fibonacci_scan_{timestamp}.xlsx",
                "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
        
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return no_update
    
    @app.callback(
        Output("download-report", "data"),
        Input("generate-report-button", "n_clicks"),
        State("batch-results-store", "data"),
        prevent_initial_call=True
    )
    def generate_html_report(n_clicks, results_data):
        """
        Generate HTML report from batch scan results
        """
        if not n_clicks or not results_data:
            return no_update
        
        try:
            # Create timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Count signal types
            buy_signals = [r for r in results_data if "Buy" in r["signal"]]
            sell_signals = [r for r in results_data if "Sell" in r["signal"]]
            
            # Generate HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Fibonacci Cycle Scanner Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1, h2, h3 {{ color: #007bff; }}
                    .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                    .summary {{ display: flex; justify-content: space-around; margin-bottom: 20px; }}
                    .summary-card {{ padding: 15px; border-radius: 5px; width: 30%; text-align: center; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .buy {{ background-color: #d4edda; }}
                    .sell {{ background-color: #f8d7da; }}
                    .footer {{ margin-top: 30px; font-size: 0.8em; color: #6c757d; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Fibonacci Cycle Scanner Report</h1>
                    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-card" style="background-color: #e9ecef;">
                        <h3>Total Signals</h3>
                        <p style="font-size: 24px;">{len(results_data)}</p>
                    </div>
                    <div class="summary-card" style="background-color: #d4edda;">
                        <h3>Buy Signals</h3>
                        <p style="font-size: 24px;">{len(buy_signals)}</p>
                    </div>
                    <div class="summary-card" style="background-color: #f8d7da;">
                        <h3>Sell Signals</h3>
                        <p style="font-size: 24px;">{len(sell_signals)}</p>
                    </div>
                </div>
                
                <h2>Buy Signals</h2>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Signal</th>
                        <th>Confidence</th>
                        <th>Strength</th>
                        <th>Cycles</th>
                    </tr>
            """
            
            # Add buy signals
            for signal in sorted(buy_signals, key=lambda x: abs(x["strength"]), reverse=True):
                cycles_str = ", ".join(map(str, signal["cycles"]))
                html_content += f"""
                    <tr class="buy">
                        <td>{signal["symbol"]}</td>
                        <td>{signal["signal"]}</td>
                        <td>{signal["confidence"]}</td>
                        <td>{signal["strength"]:.2f}</td>
                        <td>{cycles_str}</td>
                    </tr>
                """
            
            html_content += """
                </table>
                
                <h2>Sell Signals</h2>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Signal</th>
                        <th>Confidence</th>
                        <th>Strength</th>
                        <th>Cycles</th>
                    </tr>
            """
            
            # Add sell signals
            for signal in sorted(sell_signals, key=lambda x: abs(x["strength"]), reverse=True):
                cycles_str = ", ".join(map(str, signal["cycles"]))
                html_content += f"""
                    <tr class="sell">
                        <td>{signal["symbol"]}</td>
                        <td>{signal["signal"]}</td>
                        <td>{signal["confidence"]}</td>
                        <td>{signal["strength"]:.2f}</td>
                        <td>{cycles_str}</td>
                    </tr>
                """
            
            html_content += """
                </table>
                
                <div class="footer">
                    <p>Fibonacci Cycle Scanner - Trading System</p>
                    <p>Based on the discovery of universal Fibonacci market cycles</p>
                </div>
            </body>
            </html>
            """
            
            return {
                "content": html_content,
                "filename": f"fibonacci_report_{timestamp}.html",
                "type": "text/html"
            }
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
            return no_update
    
    #========================================================
    # Dashboard Callbacks
    #========================================================
    
    @app.callback(
        [
            Output("market-overview", "children"),
            Output("top-signals", "children"),
            Output("recent-crossings", "children"),
            Output("market-status", "children")
        ],
        Input("refresh-interval", "n_intervals")
    )
    def update_dashboard(n_intervals):
        """
        Update dashboard with latest market data
        """
        try:
            # In a real implementation, this would fetch the latest market data
            # Here we generate dummy data for demonstration
            
            # Market overview
            market_overview = dbc.Card(
                dbc.CardBody([
                    html.H4("Market Overview", className="card-title"),
                    html.P("Market Status: Normal", className="mb-2"),
                    html.Div([
                        html.Span("Bullish Signals: ", className="me-1"),
                        html.Span("24", className="text-success me-3"),
                        html.Span("Bearish Signals: ", className="me-1"),
                        html.Span("18", className="text-danger"),
                    ], className="mb-2"),
                    dbc.Progress(
                        value=57,  # Percent bullish
                        color="success",
                        className="mb-2"
                    ),
                    html.P(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", className="text-muted small"),
                ])
            )
            
            # Top signals
            top_signals = dbc.Card(
                dbc.CardBody([
                    html.H4("Top Signals", className="card-title"),
                    html.H5("Buy Signals", className="mt-3 mb-2"),
                    dbc.ListGroup([
                        dbc.ListGroupItem([
                            html.Div([
                                html.Strong("AAPL: ", className="me-1"),
                                html.Span("Strong Buy", className="text-success")
                            ]),
                            html.Small("Confidence: High, Strength: 2.45, Cycles: 21, 34")
                        ]),
                        dbc.ListGroupItem([
                            html.Div([
                                html.Strong("MSFT: ", className="me-1"),
                                html.Span("Buy", className="text-success")
                            ]),
                            html.Small("Confidence: Medium, Strength: 1.87, Cycles: 21, 34, 55")
                        ]),
                    ]),
                    
                    html.H5("Sell Signals", className="mt-3 mb-2"),
                    dbc.ListGroup([
                        dbc.ListGroupItem([
                            html.Div([
                                html.Strong("FB: ", className="me-1"),
                                html.Span("Strong Sell", className="text-danger")
                            ]),
                            html.Small("Confidence: High, Strength: -2.33, Cycles: 34, 55")
                        ]),
                        dbc.ListGroupItem([
                            html.Div([
                                html.Strong("NFLX: ", className="me-1"),
                                html.Span("Sell", className="text-danger")
                            ]),
                            html.Small("Confidence: Medium, Strength: -1.91, Cycles: 21, 55")
                        ]),
                    ]),
                ])
            )
            
            # Recent crossings
            recent_crossings = dbc.Card(
                dbc.CardBody([
                    html.H4("Recent Crossings", className="card-title"),
                    dbc.ListGroup([
                        dbc.ListGroupItem([
                            html.Div([
                                html.Strong("GOOGL: ", className="me-1"),
                                html.Span("Bullish 34-cycle", className="text-success")
                            ]),
                            html.Small("2 days ago")
                        ], color="success"),
                        dbc.ListGroupItem([
                            html.Div([
                                html.Strong("AMZN: ", className="me-1"),
                                html.Span("Bearish 21-cycle", className="text-danger")
                            ]),
                            html.Small("1 day ago")
                        ], color="danger"),
                        dbc.ListGroupItem([
                            html.Div([
                                html.Strong("TSLA: ", className="me-1"),
                                html.Span("Bullish 21-cycle", className="text-success")
                            ]),
                            html.Small("Today")
                        ], color="success"),
                    ]),
                ])
            )
            
            # Market status
            market_status = dbc.Card(
                dbc.CardBody([
                    html.H4("Market Cycle Status", className="card-title"),
                    
                    # Create a simple visualization of current cycle status
                    dcc.Graph(
                        figure=go.Figure(
                            data=[
                                go.Indicator(
                                    mode="gauge+number",
                                    value=65,
                                    title={"text": "Cycle Alignment"},
                                    gauge={
                                        "axis": {"range": [0, 100]},
                                        "bar": {"color": "green"},
                                        "steps": [
                                            {"range": [0, 33], "color": "red"},
                                            {"range": [33, 66], "color": "yellow"},
                                            {"range": [66, 100], "color": "green"}
                                        ],
                                        "threshold": {
                                            "line": {"color": "black", "width": 4},
                                            "thickness": 0.75,
                                            "value": 65
                                        }
                                    }
                                )
                            ],
                            layout={
                                "height": 250,
                                "margin": {"t": 0, "b": 0, "l": 0, "r": 0}
                            }
                        ),
                        config={"displayModeBar": False}
                    ),
                    
                    html.P("Moderate bullish alignment across key cycles", className="text-center")
                ])
            )
            
            return market_overview, top_signals, recent_crossings, market_status
            
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            
            # Return empty divs on error
            error_card = dbc.Card(
                dbc.CardBody([
                    html.H4("Error", className="text-danger"),
                    html.P(f"Error updating dashboard: {str(e)}")
                ])
            )
            
            return error_card, error_card, error_card, error_card
    
    #========================================================
    # Settings Callbacks
    #========================================================
    
    @app.callback(
        Output("general-settings-status", "children"),
        Input("save-general-settings", "n_clicks"),
        [
            State("default-exchange", "value"),
            State("default-interval", "value"),
            State("default-lookback", "value"),
            State("cache-max-age", "value")
        ],
        prevent_initial_call=True
    )
    def save_general_settings(n_clicks, exchange, interval, lookback, cache_max_age):
        """
        Save general settings
        """
        if not n_clicks:
            return no_update
        
        try:
            # In a real implementation, this would save to a configuration file
            # Here we just simulate the save operation
            
            # Validate inputs
            if not exchange:
                return html.Span("Exchange cannot be empty", className="text-danger")
            
            if not interval:
                return html.Span("Interval cannot be empty", className="text-danger")
            
            try:
                lookback = int(lookback)
                if lookback <= 0:
                    return html.Span("Lookback must be a positive number", className="text-danger")
            except:
                return html.Span("Lookback must be a valid number", className="text-danger")
            
            try:
                cache_max_age = int(cache_max_age)
                if cache_max_age < 0:
                    return html.Span("Cache max age cannot be negative", className="text-danger")
            except:
                return html.Span("Cache max age must be a valid number", className="text-danger")
            
            # Import configuration manager
            from utils.config_manager import config
            
            # Update configuration
            config.update_section("general", {
                "default_exchange": exchange,
                "default_interval": interval,
                "default_lookback": lookback,
                "cache_expiry": cache_max_age
            })
            
            return html.Span("Settings saved successfully", className="text-success")
            
        except Exception as e:
            logger.error(f"Error saving general settings: {e}")
            return html.Span(f"Error: {str(e)}", className="text-danger")
    
    @app.callback(
        Output("analysis-settings-status", "children"),
        Input("save-analysis-settings", "n_clicks"),
        [
            State("cycle-detection-method", "value"),
            State("min-period", "value"),
            State("max-period", "value"),
            State("fib-cycles", "value"),
            State("use-gpu", "value")
        ],
        prevent_initial_call=True
    )
    def save_analysis_settings(n_clicks, method, min_period, max_period, fib_cycles, use_gpu):
        """
        Save analysis settings
        """
        if not n_clicks:
            return no_update
        
        try:
            # Validate inputs
            if not method:
                return html.Span("Cycle detection method cannot be empty", className="text-danger")
            
            try:
                min_period = int(min_period)
                if min_period <= 0:
                    return html.Span("Minimum period must be a positive number", className="text-danger")
            except:
                return html.Span("Minimum period must be a valid number", className="text-danger")
            
            try:
                max_period = int(max_period)
                if max_period <= min_period:
                    return html.Span("Maximum period must be greater than minimum period", className="text-danger")
            except:
                return html.Span("Maximum period must be a valid number", className="text-danger")
            
            # Parse Fibonacci cycles
            try:
                cycles = [int(c.strip()) for c in fib_cycles.split(',') if c.strip()]
                if not cycles:
                    return html.Span("At least one Fibonacci cycle must be specified", className="text-danger")
            except:
                return html.Span("Fibonacci cycles must be comma-separated numbers", className="text-danger")
            
            # Import configuration manager
            from utils.config_manager import config
            
            # Update configuration
            config.update_section("analysis", {
                "cycle_detection_method": method,
                "min_period": min_period,
                "max_period": max_period,
                "fib_cycles": cycles
            })
            
            config.update_section("performance", {
                "use_gpu": "use_gpu" in use_gpu
            })
            
            return html.Span("Analysis settings saved successfully", className="text-success")
            
        except Exception as e:
            logger.error(f"Error saving analysis settings: {e}")
            return html.Span(f"Error: {str(e)}", className="text-danger")