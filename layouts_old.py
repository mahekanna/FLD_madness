import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Sidebar layout
sidebar = html.Div(
    [
        html.Div(
            [
                html.H3("Fibonacci Cycles", className="display-6"),
                html.Hr(),
            ],
            className="sidebar-header",
        ),
        html.Nav(
            [
                dbc.Nav(
                    [
                        dbc.NavLink(
                            [html.I(className="fas fa-home me-2"), "Dashboard"],
                            href="/",
                            active="exact",
                            className="mb-1",
                        ),
                        dbc.NavLink(
                            [html.I(className="fas fa-chart-line me-2"), "Symbol Analysis"],
                            href="/symbol",
                            active="exact",
                            className="mb-1",
                        ),
                        dbc.NavLink(
                            [html.I(className="fas fa-search me-2"), "Batch Scan"],
                            href="/batch",
                            active="exact",
                            className="mb-1",
                        ),
                        dbc.NavLink(
                            [html.I(className="fas fa-file-alt me-2"), "Reports"],
                            href="/reports",
                            active="exact",
                            className="mb-1",
                        ),
                        dbc.NavLink(
                            [html.I(className="fas fa-cog me-2"), "Settings"],
                            href="/settings",
                            active="exact",
                            className="mb-1",
                        ),
                    ],
                    vertical=True,
                    pills=True,
                ),
            ],
            className="sidebar-nav",
        ),
        html.Div(
            [
                html.P("Fibonacci Cycle Scanner v1.0", className="text-muted small"),
                html.P(datetime.now().strftime("%Y-%m-%d"), className="text-muted small"),
            ],
            className="sidebar-footer",
        ),
    ],
    className="sidebar",
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16rem",
        "padding": "2rem 1rem",
        "background-color": "#f8f9fa",
        "overflow-y": "auto",
    },
)

# Dashboard layout
dashboard_layout = html.Div([
    html.H1("Fibonacci Cycle Scanner Dashboard", className="mb-4"),
    
    # Market Overview Cards
    dbc.Row([
        # Market Status Card
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H4("Market Overview", className="card-title"),
                    html.P(id="market-bias", children="Market Bias: Loading...", className="mb-2"),
                    html.Div([
                        html.Span("Bullish Signals: ", className="me-1"),
                        html.Span(id="bullish-count", children="0", className="text-success me-2"),
                        html.Span("Bearish Signals: ", className="me-1"),
                        html.Span(id="bearish-count", children="0", className="text-danger"),
                    ], className="mb-2"),
                    dbc.Progress(id="market-progress", value=50, color="success", className="mb-2"),
                    html.P(id="market-update-time", children="Last Updated: Never", className="text-muted small"),
                ]),
                className="h-100"
            ),
            width=4
        ),
        
        # Cycle Alignment Card
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H4("Cycle Alignment", className="card-title"),
                    html.Div(id="cycle-alignment-graph"),
                    html.P(id="cycle-alignment-text", children="Loading cycle data...", className="mt-2"),
                ]),
                className="h-100"
            ),
            width=4
        ),
        
        # Recent Activity Card
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H4("Recent Activity", className="card-title"),
                    html.Div(id="recent-activity", children=[
                        html.P("No recent activity", className="text-muted"),
                    ]),
                ]),
                className="h-100"
            ),
            width=4
        ),
    ], className="mb-4"),
    
    # Top Signals and Crossings
    dbc.Row([
        # Top Signals
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H4("Top Signals", className="card-title"),
                    html.Div(id="top-signals-table"),
                ]),
                className="h-100"
            ),
            width=6
        ),
        
        # Recent Crossings
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H4("Recent Crossings", className="card-title"),
                    html.Div(id="recent-crossings-table"),
                ]),
                className="h-100"
            ),
            width=6
        ),
    ], className="mb-4"),
    
    # Quick Scan Section
    dbc.Card(
        dbc.CardBody([
            html.H4("Quick Scan", className="card-title"),
            dbc.Row([
                dbc.Col([
                    dbc.Input(id="quick-scan-symbol", placeholder="Enter symbol...", className="mb-2"),
                    dbc.Select(
                        id="quick-scan-interval",
                        options=[
                            {"label": "Daily", "value": "daily"},
                            {"label": "4 Hour", "value": "4h"},
                            {"label": "1 Hour", "value": "1h"},
                            {"label": "15 Min", "value": "15min"},
                        ],
                        value="daily",
                        className="mb-2",
                    ),
                ], width=4),
                dbc.Col([
                    dbc.Button("Scan", id="quick-scan-button", color="primary", className="me-2"),
                    dbc.Spinner(html.Div(id="quick-scan-loading")),
                ], width=2, className="d-flex align-items-end"),
                dbc.Col([
                    html.Div(id="quick-scan-results"),
                ], width=6),
            ]),
        ]),
        className="mb-4"
    ),
])

# Symbol analysis layout
symbol_analysis_layout = html.Div([
    html.H1("Symbol Analysis", className="mb-4"),
    
    # Symbol Input Section
    dbc.Row([
        dbc.Col([
            dbc.Input(id="symbol-input", placeholder="Enter symbol...", className="mb-2"),
        ], width=3),
        dbc.Col([
            dbc.Select(
                id="interval-select",
                options=[
                    {"label": "Daily", "value": "daily"},
                    {"label": "4 Hour", "value": "4h"},
                    {"label": "1 Hour", "value": "1h"},
                    {"label": "15 Min", "value": "15min"},
                ],
                value="daily",
                className="mb-2",
            ),
        ], width=2),
        dbc.Col([
            dbc.Button("Analyze", id="analyze-button", color="primary", className="me-2"),
            dbc.Spinner(html.Div(id="analysis-loading")),
        ], width=2),
        dbc.Col([
            dbc.Button("Multi-Timeframe Analysis", id="multi-tf-button", 
                      color="secondary", className="me-2"),
        ], width=3),
        dbc.Col([
            dbc.Button(
                [html.I(className="fas fa-save me-2"), "Save Results"], 
                id="save-analysis-button", 
                color="success", 
                className="me-2"
            ),
        ], width=2),
    ], className="mb-4"),
    
    # Results Container
    html.Div(id="analysis-results-container", children=[
        dbc.Alert(
            "Enter a symbol and click Analyze to begin.",
            color="info",
        ),
    ]),
    
    # The main results section will be populated by the callback
    html.Div(id="analysis-results"),
    
    # Hidden div for storing analysis data for export
    dcc.Store(id="analysis-data-store")
])

# Batch scan layout
batch_scan_layout = html.Div([
    html.H1("Batch Scan", className="mb-4"),
    
    # Scan Configuration Section
    dbc.Card([
        dbc.CardBody([
            html.H4("Scan Configuration", className="card-title mb-3"),
            dbc.Row([
                # Symbol Selection
                dbc.Col([
                    html.Label("Symbols Source"),
                    dbc.RadioItems(
                        id="symbols-source",
                        options=[
                            {"label": "Default Symbols List", "value": "default"},
                            {"label": "Custom Symbols", "value": "custom"},
                            {"label": "Market Index Components", "value": "index"},
                        ],
                        value="default",
                        inline=True,
                        className="mb-2",
                    ),
                    html.Div(id="symbols-source-container"),
                ], width=6),
                
                # Interval Selection
                dbc.Col([
                    html.Label("Interval"),
                    dbc.Select(
                        id="batch-interval-select",
                        options=[
                            {"label": "Daily", "value": "daily"},
                            {"label": "4 Hour", "value": "4h"},
                            {"label": "1 Hour", "value": "1h"},
                            {"label": "15 Min", "value": "15min"},
                        ],
                        value="daily",
                        className="mb-2",
                    ),
                    html.Label("Filter Settings"),
                    dbc.Checklist(
                        id="scan-filters",
                        options=[
                            {"label": "20/21-cycle signals", "value": "cycle_20_21"},
                            {"label": "34-cycle signals", "value": "cycle_34"},
                            {"label": "Recent crossings only", "value": "recent_crossing"},
                            {"label": "Use GPU acceleration (if available)", "value": "use_gpu"},
                        ],
                        value=["cycle_20_21", "cycle_34"],
                        className="mb-2",
                    ),
                ], width=6),
            ]),
            
            # Scan Button Row
            dbc.Row([
                dbc.Col([
                    dbc.Button("Start Scan", id="start-scan-button", color="primary", className="me-2"),
                    dbc.Spinner(html.Div(id="batch-scan-loading", style={"display": "inline-block"})),
                ], width=6),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="fas fa-file-csv me-2"), "Export to CSV"], 
                        id="export-csv-button", 
                        color="success", 
                        className="me-2",
                        disabled=True
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-file-excel me-2"), "Export to Excel"], 
                        id="export-excel-button", 
                        color="success", 
                        className="me-2",
                        disabled=True
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-chart-bar me-2"), "Generate Report"], 
                        id="generate-report-button", 
                        color="info",
                        disabled=True
                    ),
                ], width=6, className="text-end"),
            ]),
        ]),
    ], className="mb-4"),
    
    # Progress Bar
    html.Div(id="scan-progress-container", style={"display": "none"}, children=[
        html.Label("Scan Progress"),
        dbc.Progress(id="scan-progress", value=0, className="mb-2"),
        html.P(id="scan-status", className="text-muted small"),
    ]),
    
    # Results Section
    html.Div(id="batch-scan-results", children=[
        dbc.Alert(
            "Configure your scan settings and click Start Scan to begin.",
            color="info",
        ),
    ]),
    
    # Hidden div for storing scan results
    dcc.Store(id="batch-results-store")
])

# Reports layout
reports_layout = html.Div([
    html.H1("Reports", className="mb-4"),
    
    # Reports Navigation Tabs
    dbc.Tabs([
        dbc.Tab([
            dbc.Card(
                dbc.CardBody([
                    html.H4("Saved Reports", className="card-title mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Input(id="report-search", placeholder="Search reports...", className="mb-3"),
                        ], width=4),
                        dbc.Col([
                            dbc.Select(
                                id="report-type-filter",
                                options=[
                                    {"label": "All Types", "value": "all"},
                                    {"label": "Scan Reports", "value": "scan"},
                                    {"label": "Analysis Reports", "value": "analysis"},
                                    {"label": "Backtest Reports", "value": "backtest"},
                                ],
                                value="all",
                                className="mb-3",
                            ),
                        ], width=4),
                        dbc.Col([
                            dbc.Button("Refresh", id="refresh-reports-button", color="primary"),
                        ], width=4, className="text-end"),
                    ]),
                    
                    # Reports Table
                    html.Div(id="reports-table-container", children=[
                        dbc.Alert("No reports found. Generate a report from the Batch Scan or Symbol Analysis pages.", color="info"),
                    ]),
                ]),
            ),
        ], label="Saved Reports", tab_id="saved-reports"),
        
        dbc.Tab([
            dbc.Card(
                dbc.CardBody([
                    html.H4("Scheduled Reports", className="card-title mb-3"),
                    
                    # Scheduled Reports Configuration
                    dbc.Row([
                        dbc.Col([
                            html.Label("Report Type"),
                            dbc.Select(
                                id="scheduled-report-type",
                                options=[
                                    {"label": "Daily Market Scan", "value": "daily_scan"},
                                    {"label": "Weekly Analysis", "value": "weekly_analysis"},
                                    {"label": "Custom Symbols Scan", "value": "custom_scan"},
                                ],
                                value="daily_scan",
                                className="mb-2",
                            ),
                        ], width=4),
                        dbc.Col([
                            html.Label("Schedule"),
                            dbc.Select(
                                id="scheduled-report-frequency",
                                options=[
                                    {"label": "Daily", "value": "daily"},
                                    {"label": "Weekly", "value": "weekly"},
                                    {"label": "Monthly", "value": "monthly"},
                                ],
                                value="daily",
                                className="mb-2",
                            ),
                        ], width=4),
                        dbc.Col([
                            html.Label("Export Format"),
                            dbc.Checklist(
                                id="scheduled-report-format",
                                options=[
                                    {"label": "CSV", "value": "csv"},
                                    {"label": "Excel", "value": "excel"},
                                    {"label": "PDF", "value": "pdf"},
                                    {"label": "Email", "value": "email"},
                                    {"label": "Telegram", "value": "telegram"},
                                ],
                                value=["csv", "telegram"],
                                inline=True,
                                className="mb-2",
                            ),
                        ], width=4),
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Add Scheduled Report", id="add-scheduled-report-button", color="primary", className="mb-3"),
                        ], width=12),
                    ]),
                    
                    # Scheduled Reports Table
                    html.Div(id="scheduled-reports-table", children=[
                        dbc.Alert("No scheduled reports configured.", color="info"),
                    ]),
                ]),
            ),
        ], label="Scheduled Reports", tab_id="scheduled-reports"),
        
        dbc.Tab([
            dbc.Card(
                dbc.CardBody([
                    html.H4("Report Templates", className="card-title mb-3"),
                    
                    # Report Templates List
                    dbc.ListGroup([
                        dbc.ListGroupItem([
                            html.H5("Daily Market Summary"),
                            html.P("Overview of market with top signals and crossings"),
                            dbc.Button("Use Template", id="template-daily-button", color="primary", size="sm"),
                        ]),
                        dbc.ListGroupItem([
                            html.H5("Weekly Cycle Analysis"),
                            html.P("Detailed analysis of current market cycles and projections"),
                            dbc.Button("Use Template", id="template-weekly-button", color="primary", size="sm"),
                        ]),
                        dbc.ListGroupItem([
                            html.H5("Symbol Watchlist"),
                            html.P("Track a custom list of symbols and their cycle status"),
                            dbc.Button("Use Template", id="template-watchlist-button", color="primary", size="sm"),
                        ]),
                        dbc.ListGroupItem([
                            html.H5("Backtest Report"),
                            html.P("Detailed backtest results with performance metrics"),
                            dbc.Button("Use Template", id="template-backtest-button", color="primary", size="sm"),
                        ]),
                    ]),
                ]),
            ),
        ], label="Templates", tab_id="report-templates"),
    ], id="reports-tabs", active_tab="saved-reports"),
])

# Settings layout
settings_layout = html.Div([
    html.H1("Settings", className="mb-4"),
    
    # Settings Tabs
    dbc.Tabs([
        dbc.Tab([
            dbc.Card(
                dbc.CardBody([
                    html.H4("General Settings", className="card-title mb-3"),
                    
                    # Default Settings
                    dbc.Row([
                        dbc.Col([
                            html.Label("Default Exchange"),
                            dbc.Input(id="default-exchange", value="NSE", className="mb-2"),
                            html.Small("Exchange to use for symbol lookups", className="text-muted d-block mb-3"),
                            
                            html.Label("Default Interval"),
                            dbc.Select(
                                id="default-interval",
                                options=[
                                    {"label": "Daily", "value": "daily"},
                                    {"label": "4 Hour", "value": "4h"},
                                    {"label": "1 Hour", "value": "1h"},
                                    {"label": "15 Min", "value": "15min"},
                                ],
                                value="daily",
                                className="mb-2",
                            ),
                            html.Small("Default timeframe for analysis", className="text-muted d-block mb-3"),
                        ], width=6),
                        dbc.Col([
                            html.Label("Default Lookback Period"),
                            dbc.Input(id="default-lookback", type="number", value="5000", className="mb-2"),
                            html.Small("Number of bars to fetch for analysis", className="text-muted d-block mb-3"),
                            
                            html.Label("Data Cache Settings"),
                            dbc.Input(id="cache-max-age", type="number", value="86400", className="mb-2"),
                            html.Small("Maximum age of cached data in seconds (86400 = 24 hours)", className="text-muted d-block mb-3"),
                        ], width=6),
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Save General Settings", id="save-general-settings", color="primary"),
                            html.Div(id="general-settings-status", className="mt-2"),
                        ], width=6),
                        dbc.Col([
                            dbc.Button("Clear Data Cache", id="clear-cache-button", color="warning"),
                            html.Div(id="cache-status", className="mt-2"),
                        ], width=6),
                    ]),
                ]),
            ),
        ], label="General", tab_id="general-settings"),
        
        dbc.Tab([
            dbc.Card(
                dbc.CardBody([
                    html.H4("Analysis Settings", className="card-title mb-3"),
                    
                    # Cycle Detection Settings
                    dbc.Row([
                        dbc.Col([
                            html.Label("Cycle Detection Method"),
                            dbc.Select(
                                id="cycle-detection-method",
                                options=[
                                    {"label": "FFT Analysis", "value": "fft"},
                                    {"label": "Wavelet Analysis", "value": "wavelet"},
                                    {"label": "Combined Analysis", "value": "combined"},
                                ],
                                value="fft",
                                className="mb-2",
                            ),
                            html.Small("Method used for detecting dominant cycles", className="text-muted d-block mb-3"),
                            
                            html.Label("Min/Max Cycle Periods"),
                            dbc.InputGroup([
                                dbc.Input(id="min-cycle-period", type="number", value="20", className="mb-2"),
                                dbc.InputGroupText("to"),
                                dbc.Input(id="max-cycle-period", type="number", value="250", className="mb-2"),
                            ]),
                            html.Small("Range of cycle periods to detect", className="text-muted d-block mb-3"),
                        ], width=6),
                        dbc.Col([
                            html.Label("Fibonacci Cycle List"),
                            dbc.Input(id="fibonacci-cycles", value="20,21,34,55,89", className="mb-2"),
                            html.Small("Comma-separated list of Fibonacci cycle periods", className="text-muted d-block mb-3"),
                            
                            html.Label("Hardware Acceleration"),
                            dbc.Checklist(
                                id="use-gpu",
                                options=[
                                    {"label": "Use GPU acceleration if available", "value": "use_gpu"},
                                ],
                                value=[],
                                className="mb-2",
                            ),
                            html.Small("Requires CUDA and CuPy installation", className="text-muted d-block mb-3"),
                        ], width=6),
                    ]),
                    
                    dbc.Button("Save Analysis Settings", id="save-analysis-settings", color="primary"),
                    html.Div(id="analysis-settings-status", className="mt-2"),
                ]),
            ),
        ], label="Analysis", tab_id="analysis-settings"),
        
        dbc.Tab([
            dbc.Card(
                dbc.CardBody([
                    html.H4("Notification Settings", className="card-title mb-3"),
                    
                    # Telegram Settings
                    dbc.Row([
                        dbc.Col([
                            html.Label("Telegram Bot Token"),
                            dbc.Input(id="telegram-token", type="password", placeholder="Enter bot token...", className="mb-2"),
                            html.Small("Token for your Telegram bot from BotFather", className="text-muted d-block mb-3"),
                        ], width=6),
                        dbc.Col([
                            html.Label("Telegram Chat ID"),
                            dbc.Input(id="telegram-chat-id", placeholder="Enter chat ID...", className="mb-2"),
                            html.Small("Chat ID for sending notifications", className="text-muted d-block mb-3"),
                        ], width=6),
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            html.Label("Notification Preferences"),
                            dbc.Checklist(
                                id="notification-preferences",
                                options=[
                                    {"label": "Send scan reports", "value": "scan_reports"},
                                    {"label": "Alert on strong buy signals", "value": "strong_buys"},
                                    {"label": "Alert on strong sell signals", "value": "strong_sells"},
                                    {"label": "Alert on 34-cycle crossings", "value": "cycle_34_crossings"},
                                    {"label": "Send daily summary", "value": "daily_summary"},
                                ],
                                value=[],
                                className="mb-3",
                            ),
                        ], width=8),
                        dbc.Col([
                            dbc.Button("Test Telegram Connection", id="test-telegram", color="info", className="mb-2"),
                            html.Div(id="telegram-test-result", className="mt-2"),
                        ], width=4),
                    ]),
                    
                    dbc.Button("Save Notification Settings", id="save-notification-settings", color="primary"),
                    html.Div(id="notification-settings-status", className="mt-2"),
                ]),
            ),
        ], label="Notifications", tab_id="notification-settings"),
        
        dbc.Tab([
            dbc.Card(
                dbc.CardBody([
                    html.H4("Symbols Management", className="card-title mb-3"),
                    
                    # Symbols File Settings
                    dbc.Row([
                        dbc.Col([
                            html.Label("Symbols File Path"),
                            dbc.Input(id="symbols-file-path", placeholder="Enter file path...", className="mb-2"),
                            html.Small("Path to CSV or text file with symbols list", className="text-muted d-block mb-3"),
                        ], width=10),
                        dbc.Col([
                            dbc.Button("Browse", id="browse-symbols-file", color="secondary", className="mb-2"),
                        ], width=2),
                    ]),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Load Symbols", id="load-symbols", color="primary", className="me-2"),
                            dbc.Button("Edit Symbols", id="edit-symbols", color="info", className="me-2"),
                            dbc.Button("Download Template", id="download-symbols-template", color="secondary"),
                        ], width=12),
                    ]),
                    
                    html.Div(id="symbols-status", className="mt-3"),
                    
                    html.H5("Current Symbols", className="mt-4 mb-3"),
                    html.Div(id="symbols-table-container"),
                ]),
            ),
        ], label="Symbols", tab_id="symbols-settings"),
        
        dbc.Tab([
            dbc.Card(
                dbc.CardBody([
                    html.H4("About", className="card-title mb-3"),
                    
                    html.H5("Fibonacci Market Cycle Trading System"),
                    html.P([
                        "Version 1.0.0",
                        html.Br(),
                        "Built on the discovery of universal Fibonacci-based market cycles",
                        html.Br(),
                        "© 2023 All Rights Reserved"
                    ]),
                    
                    html.H5("System Information", className="mt-4"),
                    html.Div(id="system-info"),
                    
                    html.H5("Documentation", className="mt-4"),
                    dbc.ListGroup([
                        dbc.ListGroupItem([
                            html.I(className="fas fa-book me-2"),
                            "User Guide",
                            dbc.Button("Open", id="open-user-guide", color="link", size="sm", className="float-end"),
                        ]),
                        dbc.ListGroupItem([
                            html.I(className="fas fa-code me-2"),
                            "Developer Documentation",
                            dbc.Button("Open", id="open-developer-docs", color="link", size="sm", className="float-end"),
                        ]),
                        dbc.ListGroupItem([
                            html.I(className="fas fa-question-circle me-2"),
                            "Troubleshooting Guide",
                            dbc.Button("Open", id="open-troubleshooting", color="link", size="sm", className="float-end"),
                        ]),
                    ]),
                ]),
            ),
        ], label="About", tab_id="about-settings"),
    ], id="settings-tabs", active_tab="general-settings"),
])