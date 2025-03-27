# Upload option
                dbc.Row([
                    dbc.Col([
                        html.Label("Upload Symbols File:"),
                        dcc.Upload(
                            id='upload-symbols',
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
                    ], width=12),
                ], className="mt-3"),
                html.Div(id="upload-status", className="mt-2"),
            ])
        ]),
    ])
```

## 3. Advanced Analysis Components

### 3.1 Multi-Timeframe Analysis Implementation

```python
def analyze_multi_timeframe(symbol, timeframes=None, params=None):
    """
    Perform multi-timeframe analysis on a symbol
    
    Args:
        symbol: Trading symbol
        timeframes: List of timeframes to analyze
        params: ScanParameters object
        
    Returns:
        Dictionary with multi-timeframe analysis
    """
    if timeframes is None:
        timeframes = ["daily", "4h", "1h", "15min"]
        
    if params is None:
        params = ScanParameters()
        
    # Analyze each timeframe
    results = {}
    for timeframe in timeframes:
        try:
            result = scanner.analyze_symbol(symbol, timeframe, params)
            if result:
                results[timeframe] = result
        except Exception as e:
            logger.error(f"Error analyzing {symbol} on {timeframe}: {e}")
    
    # Skip if no valid results
    if not results:
        return None
    
    # Calculate timeframe alignment metrics
    alignment_score, alignment_direction = calculate_timeframe_alignment(results)
    
    # Determine composite signal based on all timeframes
    composite_signal = determine_composite_signal(results, alignment_score, alignment_direction)
    
    # Create integrated cycle data
    integrated_cycles = integrate_cycle_data(results)
    
    return {
        "symbol": symbol,
        "timeframe_results": results,
        "alignment_score": alignment_score,
        "alignment_direction": alignment_direction,
        "composite_signal": composite_signal,
        "integrated_cycles": integrated_cycles
    }
```

### 3.2 Timeframe Alignment Calculation

```python
def calculate_timeframe_alignment(results):
    """
    Calculate timeframe alignment metrics
    
    Args:
        results: Dictionary of ScanResult objects by timeframe
        
    Returns:
        Tuple of (alignment_score, alignment_direction)
    """
    if not results:
        return 0, "neutral"
    
    # Count bullish and bearish timeframes
    bullish_count = sum(1 for r in results.values() if r.combined_strength > 0)
    bearish_count = sum(1 for r in results.values() if r.combined_strength < 0)
    
    # Calculate weighted signal strength
    # Weight timeframes: daily > 4h > 1h > 15min
    timeframe_weights = {
        "weekly": 2.0,
        "daily": 1.5,
        "4h": 1.0,
        "1h": 0.8,
        "15min": 0.6,
        "5min": 0.4
    }
    
    weighted_strength = sum(
        results[tf].combined_strength * timeframe_weights.get(tf, 1.0)
        for tf in results
    )
    
    # Normalize by total weight
    total_weight = sum(timeframe_weights.get(tf, 1.0) for tf in results)
    if total_weight > 0:
        weighted_strength /= total_weight
    
    # Calculate alignment percentage
    total_timeframes = len(results)
    if total_timeframes > 0:
        max_aligned = max(bullish_count, bearish_count)
        alignment_percentage = max_aligned / total_timeframes
    else:
        alignment_percentage = 0
    
    # Calculate final alignment score
    alignment_score = alignment_percentage * abs(weighted_strength)
    
    # Determine direction
    if weighted_strength > 0:
        alignment_direction = "bullish"
    elif weighted_strength < 0:
        alignment_direction = "bearish"
    else:
        alignment_direction = "neutral"
    
    return alignment_score, alignment_direction
```

### 3.3 Backtest Engine Implementation

```python
class BacktestEngine:
    """Backtesting engine for Fibonacci cycle strategies"""
    
    def __init__(self, data, params=None):
        """
        Initialize backtest engine
        
        Args:
            data: DataFrame with historical price data
            params: ScanParameters object
        """
        self.data = data.copy()
        self.params = params or ScanParameters()
        self.results = {}
        
    def run_backtest(self, strategy_type="fld_crossover", stop_loss_type="atr", 
                    take_profit_type="next_cycle", position_sizing="fixed"):
        """
        Run backtest with specified strategy parameters
        
        Args:
            strategy_type: Strategy type (fld_crossover, dual_cycle, etc.)
            stop_loss_type: Stop loss type (atr, cycle_extreme, etc.)
            take_profit_type: Take profit type (next_cycle, fib_extension, etc.)
            position_sizing: Position sizing method (fixed, risk_based, etc.)
            
        Returns:
            Dictionary with backtest results
        """
        # Reset results
        self.results = {}
        
        # Initialize strategy
        if strategy_type == "fld_crossover":
            strategy = FLDCrossoverStrategy(
                self.data, self.params, 
                stop_loss_type, take_profit_type, position_sizing
            )
        elif strategy_type == "dual_cycle":
            strategy = DualCycleStrategy(
                self.data, self.params, 
                stop_loss_type, take_profit_type, position_sizing
            )
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        # Run the strategy
        trades, equity_curve = strategy.run()
        
        # Calculate performance metrics
        metrics = self.calculate_performance_metrics(trades, equity_curve)
        
        # Store results
        self.results = {
            "trades": trades,
            "equity_curve": equity_curve,
            "metrics": metrics,
            "parameters": {
                "strategy_type": strategy_type,
                "stop_loss_type": stop_loss_type,
                "take_profit_type": take_profit_type,
                "position_sizing": position_sizing
            }
        }
        
        return self.results
    
    def calculate_performance_metrics(self, trades, equity_curve):
        """
        Calculate performance metrics for backtest
        
        Args:
            trades: List of trade dictionaries
            equity_curve: DataFrame with equity curve
            
        Returns:
            Dictionary with performance metrics
        """
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "avg_return": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "sortino_ratio": 0
            }
        
        # Calculate basic metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['profit_pct'] > 0]
        losing_trades = [t for t in trades if t['profit_pct'] <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        gross_profit = sum(t['profit_pct'] for t in winning_trades)
        gross_loss = abs(sum(t['profit_pct'] for t in losing_trades))
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_return = sum(t['profit_pct'] for t in trades) / total_trades if total_trades > 0 else 0
        
        # Calculate drawdown
        max_drawdown = 0
        peak = 1.0
        
        for value in equity_curve['equity']:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate Sharpe and Sortino ratios
        if len(equity_curve) > 1:
            returns = equity_curve['equity'].pct_change().dropna()
            
            avg_return = returns.mean()
            std_dev = returns.std()
            
            # Sharpe ratio (annualized)
            sharpe_ratio = (avg_return / std_dev) * np.sqrt(252) if std_dev > 0 else 0
            
            # Sortino ratio (using only negative returns)
            neg_returns = returns[returns < 0]
            downside_dev = neg_returns.std()
            
            sortino_ratio = (avg_return / downside_dev) * np.sqrt(252) if downside_dev > 0 else 0
        else:
            sharpe_ratio = 0
            sortino_ratio = 0
        
        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_return": avg_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "total_return": equity_curve['equity'].iloc[-1] - 1.0 if len(equity_curve) > 0 else 0
        }
    
    def optimize_parameters(self, param_grid, strategy_type="fld_crossover"):
        """
        Optimize strategy parameters using grid search
        
        Args:
            param_grid: Dictionary with parameter grids
            strategy_type: Strategy type
            
        Returns:
            Dictionary with optimization results
        """
        # Generate parameter combinations
        from itertools import product
        
        param_keys = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        combinations = list(product(*param_values))
        
        # Track best parameters
        best_result = None
        best_params = None
        best_metric = -float('inf')
        optimization_metric = 'sharpe_ratio'  # Metric to optimize
        
        results = []
        
        # Test each combination
        for i, combo in enumerate(combinations):
            # Create parameter dictionary
            params = {key: value for key, value in zip(param_keys, combo)}
            
            # Run backtest with these parameters
            result = self.run_backtest(
                strategy_type=strategy_type,
                **{k: v for k, v in params.items() if k in [
                    'stop_loss_type', 'take_profit_type', 'position_sizing'
                ]}
            )
            
            # Extract optimization metric
            metric_value = result['metrics'][optimization_metric]
            
            # Update best if improved
            if metric_value > best_metric:
                best_metric = metric_value
                best_params = params
                best_result = result
            
            # Store result
            results.append({
                'params': params,
                'metrics': result['metrics']
            })
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'all_results': results
        }
    
    def plot_equity_curve(self, figsize=(10, 6)):
        """
        Plot equity curve from backtest
        
        Args:
            figsize: Figure size tuple
            
        Returns:
            Matplotlib figure
        """
        if 'equity_curve' not in self.results:
            raise ValueError("No backtest results available. Run backtest first.")
        
        equity_curve = self.results['equity_curve']
        trades = self.results['trades']
        metrics = self.results['metrics']
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot equity curve
        ax.plot(equity_curve.index, equity_curve['equity'], label='Equity Curve', linewidth=2)
        
        # Add equity highwater mark
        highwater = equity_curve['equity'].cummax()
        ax.plot(equity_curve.index, highwater, '--', color='gray', alpha=0.5, label='Highwater Mark')
        
        # Shade drawdowns
        for i in range(len(equity_curve)):
            if equity_curve['equity'].iloc[i] < highwater.iloc[i]:
                ax.fill_between(
                    [equity_curve.index[i]], 
                    [equity_curve['equity'].iloc[i]], 
                    [highwater.iloc[i]], 
                    color='red', 
                    alpha=0.3
                )
        
        # Add trade markers
        for trade in trades:
            if trade['type'] == 'buy':
                marker = '^'
                color = 'green'
            else:
                marker = 'v'
                color = 'red'
            
            # Entry marker
            ax.plot(
                trade['entry_date'], 
                equity_curve.loc[equity_curve.index == trade['entry_date'], 'equity'].iloc[0], 
                marker=marker, 
                color=color, 
                markersize=10, 
                alpha=0.7
            )
            
            # Exit marker (square)
            ax.plot(
                trade['exit_date'], 
                equity_curve.loc[equity_curve.index == trade['exit_date'], 'equity'].iloc[0], 
                marker='s', 
                color=color if trade['profit_pct'] > 0 else 'red', 
                markersize=10, 
                alpha=0.7
            )
        
        # Add key metrics as text
        metrics_text = (
            f"Total Return: {metrics['total_return']:.2%}\n"
            f"Win Rate: {metrics['win_rate']:.2%}\n"
            f"Profit Factor: {metrics['profit_factor']:.2f}\n"
            f"Max Drawdown: {metrics['max_drawdown']:.2%}\n"
            f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n"
            f"Total Trades: {metrics['total_trades']}"
        )
        
        # Add text box with metrics
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.05, 0.95, metrics_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=props)
        
        # Format chart
        ax.set_title('Backtest Equity Curve')
        ax.set_xlabel('Date')
        ax.set_ylabel('Equity (Starting = 1.0)')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        return fig
```

### 3.4 Enhanced Trading Strategies (for Backtesting)

```python
class FLDCrossoverStrategy:
    """FLD Crossover trading strategy for backtesting"""
    
    def __init__(self, data, params, stop_loss_type="atr", 
                take_profit_type="next_cycle", position_sizing="fixed"):