import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def create_loading_card(id_prefix, message="Loading..."):
    """
    Create a loading card component
    
    Args:
        id_prefix: ID prefix for components
        message: Loading message
        
    Returns:
        Dash component
    """
    return dbc.Card(
        dbc.CardBody([
            dbc.Spinner(size="md", color="primary"),
            html.P(message, className="text-center mt-3"),
        ]),
        className="mb-4 text-center py-5"
    )

def create_error_card(error_message):
    """
    Create an error card component
    
    Args:
        error_message: Error message to display
        
    Returns:
        Dash component
    """
    return dbc.Card(
        dbc.CardBody([
            html.H4("Error", className="text-danger"),
            html.P(error_message),
            dbc.Button("Retry", id="retry-button", color="primary", className="mt-3"),
        ]),
        className="mb-4 border-danger"
    )

def create_signal_card(symbol, signal, confidence, strength, cycles, last_price=None, last_date=None):
    """
    Create a signal card component
    
    Args:
        symbol: Trading symbol
        signal: Trading signal
        confidence: Signal confidence
        strength: Signal strength
        cycles: Detected cycles
        last_price: Last price (optional)
        last_date: Last date (optional)
        
    Returns:
        Dash component
    """
    # Determine card color based on signal
    card_color = "success" if "Buy" in signal else "danger" if "Sell" in signal else "secondary"
    
    return dbc.Card(
        dbc.CardBody([
            html.H5(symbol, className="card-title"),
            html.H6(signal, className=f"text-{card_color}"),
            html.Div([
                html.Span("Confidence: ", className="small text-muted"),
                html.Span(confidence, className="small")
            ], className="mb-1"),
            html.Div([
                html.Span("Strength: ", className="small text-muted"),
                html.Span(f"{strength:.2f}", className="small")
            ], className="mb-1"),
            html.Div([
                html.Span("Cycles: ", className="small text-muted"),
                html.Span(", ".join(str(c) for c in cycles), className="small")
            ], className="mb-1"),
            html.Hr(className="my-2"),
            html.Div([
                html.Span(f"Price: {last_price:.2f}" if last_price else "", className="small me-2"),
                html.Span(last_date if last_date else "", className="small text-muted")
            ]),
            dbc.Button("View", color="primary", size="sm", className="mt-2", style={"width": "100%"}),
        ]),
        className=f"mb-3 border-{card_color}"
    )

def create_mini_chart(data, height=100, margin=10):
    """
    Create a mini chart component
    
    Args:
        data: Price data
        height: Chart height
        margin: Chart margin
        
    Returns:
        Dash component
    """
    # Create figure
    fig = go.Figure()
    
    # Add price line
    fig.add_trace(go.Scatter(
        x=list(range(len(data))),
        y=data,
        mode='lines',
        line=dict(color='black', width=1.5),
        showlegend=False
    ))
    
    # Update layout
    fig.update_layout(
        height=height,
        margin=dict(l=margin, r=margin, t=margin, b=margin),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False
        )
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

def create_cycle_badges(cycles, max_cycles=3):
    """
    Create cycle badges component
    
    Args:
        cycles: List of cycle periods
        max_cycles: Maximum number of cycles to show
        
    Returns:
        Dash component
    """
    badges = []
    
    # Colors for different cycles
    cycle_colors = {
        20: "primary",
        21: "primary",
        34: "success",
        55: "warning",
        89: "danger",
        144: "info",
        233: "secondary"
    }
    
    # Create badges for each cycle
    for i, cycle in enumerate(cycles[:max_cycles]):
        color = cycle_colors.get(cycle, "secondary")
        badges.append(dbc.Badge(str(cycle), color=color, className="me-1"))
    
    # Add "more" badge if necessary
    if len(cycles) > max_cycles:
        badges.append(dbc.Badge(f"+{len(cycles) - max_cycles} more", color="light", text_color="dark", className="me-1"))
    
    return html.Div(badges)

def create_progress_card(title, value, min_value=0, max_value=100, color="primary", description=None):
    """
    Create a progress card component
    
    Args:
        title: Card title
        value: Progress value
        min_value: Minimum value
        max_value: Maximum value
        color: Progress bar color
        description: Description text (optional)
        
    Returns:
        Dash component
    """
    # Calculate percentage
    percentage = (value - min_value) / (max_value - min_value) * 100
    
    return dbc.Card(
        dbc.CardBody([
            html.H6(title, className="card-title"),
            dbc.Progress(value=percentage, color=color, className="mb-2"),
            html.Div([
                html.Span(f"{value}", className="h5"),
                html.Span(f" / {max_value}", className="text-muted small")
            ]),
            html.P(description, className="text-muted small mb-0") if description else None,
        ]),
        className="mb-3"
    )

def create_confirmation_modal(id_prefix, title, message, confirm_text="Confirm", cancel_text="Cancel"):
    """
    Create a confirmation modal component
    
    Args:
        id_prefix: ID prefix for components
        title: Modal title
        message: Modal message
        confirm_text: Confirmation button text
        cancel_text: Cancel button text
        
    Returns:
        Dash component
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(title),
            dbc.ModalBody(message),
            dbc.ModalFooter([
                dbc.Button(
                    cancel_text, 
                    id=f"{id_prefix}-cancel-button", 
                    className="me-2", 
                    color="secondary"
                ),
                dbc.Button(
                    confirm_text, 
                    id=f"{id_prefix}-confirm-button", 
                    color="primary"
                ),
            ]),
        ],
        id=f"{id_prefix}-modal",
        centered=True,
    )

def create_data_table(data, id_suffix="table", pagination=True, page_size=10, sort_action="native", filter_action="native"):
    """
    Create a data table component
    
    Args:
        data: DataFrame or list of dictionaries
        id_suffix: ID suffix for table
        pagination: Enable pagination
        page_size: Page size
        sort_action: Sort action
        filter_action: Filter action
        
    Returns:
        Dash DataTable component
    """
    from dash import dash_table
    
    # Convert to DataFrame if necessary
    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)
    
    # Generate columns configuration
    columns = [{"name": col, "id": col} for col in data.columns]
    
    # Create DataTable
    table = dash_table.DataTable(
        id=f"data-{id_suffix}",
        columns=columns,
        data=data.to_dict("records"),
        page_size=page_size,
        page_action="native" if pagination else "none",
        sort_action=sort_action,
        filter_action=filter_action,
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "rgb(240, 240, 240)",
            "fontWeight": "bold"
        },
        style_cell={
            "padding": "10px",
            "textAlign": "left"
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)"
            }
        ]
    )
    
    return table

def create_fld_crossings_table(crossings):
    """
    Create a table displaying FLD crossings
    
    Args:
        crossings: List of crossing events
        
    Returns:
        Dash component
    """
    if not crossings:
        return html.P("No crossings detected", className="text-muted")
    
    # Create table header
    header = html.Thead(html.Tr([
        html.Th("Date"),
        html.Th("Cycle"),
        html.Th("Type"),
        html.Th("Price"),
    ]))
    
    # Create table rows
    rows = []
    for crossing in crossings:
        row_class = "table-success" if crossing["type"] == "bullish" else "table-danger"
        rows.append(html.Tr([
            html.Td(crossing["date"]),
            html.Td(crossing["cycle"]),
            html.Td(crossing["type"].capitalize()),
            html.Td(f"{crossing['price']:.2f}"),
        ], className=row_class))
    
    # Create table body
    body = html.Tbody(rows)
    
    # Create table
    return dbc.Table([header, body], bordered=True, striped=True, hover=True, size="sm")

def create_cycle_analysis_card(cycle_data):
    """
    Create a card displaying cycle analysis
    
    Args:
        cycle_data: Dictionary with cycle information
        
    Returns:
        Dash component
    """
    # Extract cycle information
    cycle = cycle_data.get("cycle", 0)
    bullish = cycle_data.get("bullish", False)
    power = cycle_data.get("power", 0)
    fld_value = cycle_data.get("fld_value", 0)
    recent_crossover = cycle_data.get("recent_crossover", False)
    recent_crossunder = cycle_data.get("recent_crossunder", False)
    
    # Determine status indicators
    status_color = "success" if bullish else "danger"
    status_text = "Bullish" if bullish else "Bearish"
    
    # Create crossing status
    if recent_crossover:
        crossing_text = "Recent bullish crossing"
        crossing_color = "success"
    elif recent_crossunder:
        crossing_text = "Recent bearish crossing"
        crossing_color = "danger"
    else:
        crossing_text = "No recent crossing"
        crossing_color = "secondary"
    
    return dbc.Card([
        dbc.CardHeader([
            html.H5(f"Cycle {cycle}", className="mb-0"),
            html.Span(f"FLD: {fld_value:.2f}", className="small text-muted d-block")
        ]),
        dbc.CardBody([
            html.Div([
                html.Span("Status: ", className="me-1"),
                html.Span(status_text, className=f"text-{status_color} fw-bold")
            ], className="mb-2"),
            html.Div([
                html.Span("Power: ", className="me-1"),
                dbc.Progress(value=power*100, color=status_color, className="mb-2")
            ]),
            html.Div([
                dbc.Badge(crossing_text, color=crossing_color, className="mt-2")
            ])
        ])
    ], className="mb-3")

def create_trading_recommendation_card(guidance):
    """
    Create a card displaying trading recommendations
    
    Args:
        guidance: Dictionary with trading guidance
        
    Returns:
        Dash component
    """
    # Extract guidance information
    action = guidance.get("action", "Hold")
    entry_strategy = guidance.get("entry_strategy", "")
    exit_strategy = guidance.get("exit_strategy", "")
    stop_loss = guidance.get("stop_loss")
    target = guidance.get("target")
    position_size = guidance.get("position_size", 0)
    timeframe = guidance.get("timeframe", "Medium-term")
    
    # Determine action color
    action_color = "success" if action == "Buy" else "danger" if action == "Sell" else "secondary"
    
    return dbc.Card([
        dbc.CardHeader(html.H5("Trading Recommendation", className="mb-0")),
        dbc.CardBody([
            html.Div([
                html.Span("Action: ", className="me-1"),
                html.Span(action, className=f"text-{action_color} fw-bold")
            ], className="mb-3"),
            
            html.Div([
                html.H6("Entry Strategy:", className="mb-2"),
                html.P(entry_strategy, className="small")
            ], className="mb-3"),
            
            html.Div([
                html.H6("Exit Strategy:", className="mb-2"),
                html.P(exit_strategy, className="small")
            ], className="mb-3"),
            
            html.Div([
                html.H6("Risk Management:", className="mb-2"),
                
                html.Div([
                    html.Span("Stop Loss: ", className="me-1"),
                    html.Span(f"{stop_loss:.2f}" if stop_loss else "N/A", className="fw-bold")
                ], className="mb-1"),
                
                html.Div([
                    html.Span("Target: ", className="me-1"),
                    html.Span(f"{target:.2f}" if target else "N/A", className="fw-bold")
                ], className="mb-1"),
                
                html.Div([
                    html.Span("Position Size: ", className="me-1"),
                    html.Span(f"{int(position_size * 100)}%", className="fw-bold")
                ], className="mb-1"),
                
                html.Div([
                    html.Span("Timeframe: ", className="me-1"),
                    html.Span(timeframe, className="fw-bold")
                ], className="mb-1"),
            ])
        ])
    ])

def create_backtest_summary_card(metrics):
    """
    Create a card displaying backtest summary
    
    Args:
        metrics: Dictionary with backtest metrics
        
    Returns:
        Dash component
    """
    # Extract metrics
    total_return = metrics.get("total_return", 0)
    win_rate = metrics.get("win_rate", 0)
    profit_factor = metrics.get("profit_factor", 0)
    max_drawdown = metrics.get("max_drawdown", 0)
    sharpe_ratio = metrics.get("sharpe_ratio", 0)
    total_trades = metrics.get("total_trades", 0)
    winning_trades = metrics.get("winning_trades", 0)
    losing_trades = metrics.get("losing_trades", 0)
    
    # Determine overall color based on performance
    overall_color = "success" if total_return > 0 and sharpe_ratio > 1 else "warning" if total_return > 0 else "danger"
    
    return dbc.Card([
        dbc.CardHeader(html.H5("Backtest Summary", className="mb-0")),
        dbc.CardBody([
            # Key metrics at the top
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Span("Total Return: ", className="me-1"),
                        html.Span(f"{total_return:.2%}", className=f"text-{'success' if total_return > 0 else 'danger'} fw-bold")
                    ], className="mb-2"),
                    
                    html.Div([
                        html.Span("Win Rate: ", className="me-1"),
                        html.Span(f"{win_rate:.2%}", className="fw-bold")
                    ], className="mb-2"),
                ], width=6),
                
                dbc.Col([
                    html.Div([
                        html.Span("Profit Factor: ", className="me-1"),
                        html.Span(f"{profit_factor:.2f}", className=f"text-{'success' if profit_factor > 1 else 'danger'} fw-bold")
                    ], className="mb-2"),
                    
                    html.Div([
                        html.Span("Max Drawdown: ", className="me-1"),
                        html.Span(f"{max_drawdown:.2%}", className="text-danger fw-bold")
                    ], className="mb-2"),
                ], width=6),
            ], className="mb-3"),
            
            # Secondary metrics
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Span("Sharpe Ratio: ", className="me-1"),
                        html.Span(f"{sharpe_ratio:.2f}", className=f"text-{'success' if sharpe_ratio > 1 else 'secondary'} fw-bold")
                    ], className="mb-2"),
                ], width=6),
                
                dbc.Col([
                    html.Div([
                        html.Span("Total Trades: ", className="me-1"),
                        html.Span(f"{total_trades}", className="fw-bold")
                    ], className="mb-2"),
                ], width=6),
            ], className="mb-3"),
            
            # Win/Loss breakdown
            html.Div([
                html.Span(f"Winning Trades: {winning_trades}", className="text-success me-3"),
                html.Span(f"Losing Trades: {losing_trades}", className="text-danger"),
            ], className="small"),
            
            # Overall assessment
            dbc.Alert(
                "Strategy shows positive results" if total_return > 0 and sharpe_ratio > 1 else
                "Strategy is profitable but with significant drawdowns" if total_return > 0 else
                "Strategy does not perform well",
                color=overall_color,
                className="mt-3 mb-0"
            )
        ])
    ])

def create_system_info_card(info):
    """
    Create a card displaying system information
    
    Args:
        info: Dictionary with system information
        
    Returns:
        Dash component
    """
    # Extract system info
    version = info.get("version", "1.0.0")
    platform = info.get("platform", "Unknown")
    python_version = info.get("python_version", "Unknown")
    memory_usage = info.get("memory_usage", 0)
    disk_usage = info.get("disk_usage", 0)
    gpu_available = info.get("gpu_available", False)
    talib_version = info.get("talib_version", "Unknown")
    
    return dbc.Card([
        dbc.CardHeader(html.H5("System Information", className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.P([
                        html.Strong("Version: "),
                        html.Span(version)
                    ], className="mb-2"),
                    
                    html.P([
                        html.Strong("Platform: "),
                        html.Span(platform)
                    ], className="mb-2"),
                    
                    html.P([
                        html.Strong("Python Version: "),
                        html.Span(python_version)
                    ], className="mb-2"),
                ], width=6),
                
                dbc.Col([
                    html.P([
                        html.Strong("Memory Usage: "),
                        html.Span(f"{memory_usage:.2f} MB")
                    ], className="mb-2"),
                    
                    html.P([
                        html.Strong("Disk Usage: "),
                        html.Span(f"{disk_usage:.2f} MB")
                    ], className="mb-2"),
                    
                    html.P([
                        html.Strong("GPU Acceleration: "),
                        html.Span("Available" if gpu_available else "Not Available", 
                                 className=f"text-{'success' if gpu_available else 'secondary'}")
                    ], className="mb-2"),
                ], width=6),
            ]),
            
            html.P([
                html.Strong("TA-Lib Version: "),
                html.Span(talib_version)
            ], className="mb-2"),
        ])
    ])