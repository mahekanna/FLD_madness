import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
import os
import time
import io
import base64
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import core components
from .cycle_detection import detect_cycles, detect_cycle_extremes, generate_cycle_wave
from .fld_calculation import calculate_fld, detect_fld_crossings, calculate_cycle_state
from .signal_generation import calculate_combined_strength, determine_signal, generate_position_guidance
from .data_manager import DataManager

logger = logging.getLogger(__name__)

@dataclass
class ScanParameters:
    """Parameters for cycle scanning"""
    min_period: int = 20
    max_period: int = 250
    num_cycles: int = 3
    lookback: int = 5000
    use_gpu: bool = False
    fib_cycles: List[int] = None
    
    def __post_init__(self):
        if self.fib_cycles is None:
            self.fib_cycles = [20, 21, 34, 55, 89]

@dataclass
class ScanResult:
    """Result of scanning a single symbol"""
    symbol: str
    interval: str
    last_price: float
    last_date: str
    cycles: List[int]
    powers: List[float]
    cycle_states: Dict[int, Dict]
    combined_strength: float
    has_key_cycles: bool
    signal: str
    confidence: str
    plot_data: Dict
    guidance: Dict
    
class FibCycleScanner:
    """
    Scanner for detecting Fibonacci cycles and generating trading signals
    """
    
    def __init__(self, exchange="NSE", output_dir="./data/reports"):
        """
        Initialize scanner
        
        Args:
            exchange: Default exchange to use
            output_dir: Directory for saving reports and plots
        """
        self.exchange = exchange
        self.output_dir = output_dir
        self.data_manager = DataManager()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Scanner initialized with exchange {exchange}")
    
    def analyze_symbol(self, symbol, interval_name, params=None):
        """
        Analyze a single symbol
        
        Args:
            symbol: Symbol to analyze
            interval_name: Interval name (e.g., 'daily', '15min')
            params: Scan parameters or None to use defaults
            
        Returns:
            ScanResult object or None if analysis fails
        """
        if params is None:
            params = ScanParameters()
            
        try:
            # Fetch data
            data = self.data_manager.get_data(
                symbol=symbol,
                exchange=self.exchange,
                interval=interval_name,
                n_bars=params.lookback
            )
            
            if data is None or len(data) < 100:
                logger.warning(f"Insufficient data for {symbol} on {interval_name}")
                return None
            
            # Get price series for analysis (HLC3)
            if all(col in data.columns for col in ['high', 'low', 'close']):
                price_series = (data['high'] + data['low'] + data['close']) / 3
            else:
                price_series = data['close']
            
            # Detect dominant cycles
            detected_cycles, cycle_powers = detect_cycles(
                data=price_series,
                min_periods=params.min_period,
                max_periods=params.max_period,
                num_cycles=params.num_cycles,
                use_gpu=params.use_gpu
            )
            
            # Skip if no significant cycles found
            if len(detected_cycles) == 0:
                logger.warning(f"No significant cycles found for {symbol}")
                return None
            
            # Calculate FLDs and cycle states
            flds = {}
            cycle_states = {}
            
            for i, cycle in enumerate(detected_cycles):
                # Calculate FLD
                fld = calculate_fld(data, cycle)
                flds[cycle] = fld
                
                # Calculate cycle state
                state = calculate_cycle_state(data, cycle, fld)
                
                # Add power from cycle detection
                if i < len(cycle_powers):
                    state['power'] = float(cycle_powers[i])
                
                cycle_states[cycle] = state
            
            # Check if we have key Fibonacci cycles
            has_key_cycles = any(c in [20, 21] for c in detected_cycles) and (34 in detected_cycles)
            
            # Calculate combined strength
            combined_strength = calculate_combined_strength(cycle_states)
            
            # Determine signal and confidence
            signal, confidence = determine_signal(cycle_states, combined_strength)
            
            # Generate position guidance
            guidance = generate_position_guidance(
                signal, 
                confidence,
                data['close'].iloc[-1],
                cycle_states
            )
            
            # Generate plot data
            plot_data = self._generate_plot_data(symbol, data, detected_cycles, cycle_states, flds)
            
            # Create result
            result = ScanResult(
                symbol=symbol,
                interval=interval_name,
                last_price=float(data['close'].iloc[-1]),
                last_date=data.index[-1].strftime('%Y-%m-%d %H:%M') if hasattr(data.index[-1], 'strftime') else str(data.index[-1]),
                cycles=detected_cycles.tolist(),
                powers=cycle_powers.tolist(),
                cycle_states={int(k): v for k, v in cycle_states.items()},
                combined_strength=combined_strength,
                has_key_cycles=has_key_cycles,
                signal=signal,
                confidence=confidence,
                plot_data=plot_data,
                guidance=guidance
            )
            
            logger.info(f"Analysis completed for {symbol} on {interval_name}: {signal} ({confidence})")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} on {interval_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def scan_batch(self, symbols, interval_name, params=None, max_workers=5):
        """
        Scan a batch of symbols
        
        Args:
            symbols: List of symbols to scan
            interval_name: Interval name (e.g., 'daily', '15min')
            params: Scan parameters or None to use defaults
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of ScanResult objects
        """
        if params is None:
            params = ScanParameters()
            
        results = []
        
        # Process in smaller batches to avoid rate limiting
        batch_size = 10
        batch_delay = 2  # seconds
        total_batches = (len(symbols) + batch_size - 1) // batch_size
        
        logger.info(f"Scanning {len(symbols)} symbols on {interval_name} in {total_batches} batches")
        
        for batch_idx in range(total_batches):
            # Get batch
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(symbols))
            batch_symbols = symbols[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_idx+1}/{total_batches} ({len(batch_symbols)} symbols)")
            
            batch_results = []
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                futures = {executor.submit(self.analyze_symbol, symbol, interval_name, params): symbol 
                          for symbol in batch_symbols}
                
                # Process results as they complete
                for future in as_completed(futures):
                    symbol = futures[future]
                    try:
                        result = future.result()
                        if result is not None:
                            batch_results.append(result)
                    except Exception as e:
                        logger.error(f"Error processing {symbol} result: {e}")
            
            # Add batch results to overall results
            results.extend(batch_results)
            
            # Add delay between batches to avoid rate limiting
            if batch_idx < total_batches - 1:
                time.sleep(batch_delay)
        
        # Sort results by absolute combined strength
        results.sort(key=lambda x: abs(x.combined_strength), reverse=True)
        
        logger.info(f"Scan completed with {len(results)} results")
        return results
    
    def _generate_plot_data(self, symbol, data, cycles, cycle_states, flds):
        """
        Generate plot data for visualization
        
        Args:
            symbol: Symbol
            data: Price data
            cycles: Detected cycles
            cycle_states: Cycle states
            flds: FLDs by cycle
            
        Returns:
            Dictionary with plot data
        """
        try:
            # Use last 250 bars for visualization
            visible_bars = min(250, len(data))
            plot_data = data.iloc[-visible_bars:].copy()
            
            # Prepare result
            result = {
                'symbol': symbol,
                'dates': [d.strftime('%Y-%m-%d %H:%M') if hasattr(d, 'strftime') else str(d) 
                          for d in plot_data.index],
                'open': plot_data['open'].tolist() if 'open' in plot_data else [],
                'high': plot_data['high'].tolist() if 'high' in plot_data else [],
                'low': plot_data['low'].tolist() if 'low' in plot_data else [],
                'close': plot_data['close'].tolist(),
                'volume': plot_data['volume'].tolist() if 'volume' in plot_data else [],
                'cycles': {},
                'crossings': []
            }
            
            # Add cycle colors
            cycle_colors = {
                20: '#1f77b4',  # blue
                21: '#1f77b4',  # blue (same as 20)
                34: '#ff7f0e',  # orange
                55: '#2ca02c',  # green
                89: '#d62728',  # red
                144: '#9467bd',  # purple
                233: '#8c564b'   # brown
            }
            
            # Add cycle FLDs and synthetic waves
            for cycle in cycles:
                cycle = int(cycle)
                
                if cycle not in flds:
                    continue
                    
                fld = flds[cycle]
                
                # Get cycle color
                color = cycle_colors.get(cycle, '#7f7f7f')  # default gray
                
                # Add to cycle data
                result['cycles'][cycle] = {
                    'fld': fld.iloc[-visible_bars:].tolist(),
                    'bullish': cycle_states[cycle]['bullish'],
                    'color': color
                }
                
                # Generate synthetic wave
                try:
                    # Create visible window for wave
                    wave_length = 100  # last 100 bars
                    if len(plot_data) >= wave_length:
                        # Detect tops and bottoms for this cycle
                        if all(col in plot_data.columns for col in ['high', 'low', 'close']):
                            price_series = (plot_data['high'] + plot_data['low'] + plot_data['close']) / 3
                        else:
                            price_series = plot_data['close']
                            
                        peaks, troughs, _, _ = detect_cycle_extremes(price_series, cycle)
                        
                        # Get phase from recent peaks/troughs
                        phase = 0
                        if len(peaks) > 0:
                            last_peak = peaks[-1]
                            phase = 2 * np.pi * (last_peak / cycle)
                        elif len(troughs) > 0:
                            last_trough = troughs[-1]
                            phase = 2 * np.pi * (last_trough / cycle) + np.pi  # shift by 180 degrees
                        
                        # Generate wave
                        wave = generate_cycle_wave(cycle, wave_length, -phase)
                        
                        # Scale wave to price range
                        price_min = price_series.min()
                        price_max = price_series.max()
                        price_range = price_max - price_min
                        price_mid = (price_max + price_min) / 2
                        
                        wave = (wave * (price_range * 0.25)) + price_mid
                        
                        # Add to result
                        result['cycles'][cycle]['wave'] = wave.tolist()
                except Exception as e:
                    logger.error(f"Error generating wave for cycle {cycle}: {e}")
                
                # Detect crossings
                crossings = detect_fld_crossings(data.iloc[-visible_bars:], fld.iloc[-visible_bars:])
                
                # Add crossings to result
                for idx, row in crossings.iterrows():
                    date_idx = list(plot_data.index).index(idx) if idx in plot_data.index else -1
                    if date_idx >= 0:
                        crossing_type = 'bullish' if row['crossing'] > 0 else 'bearish'
                        result['crossings'].append({
                            'index': date_idx,
                            'date': result['dates'][date_idx],
                            'price': float(row['price']),
                            'type': crossing_type,
                            'cycle': int(cycle)
                        })
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating plot data: {e}")
            return {
                'symbol': symbol,
                'dates': [],
                'open': [],
                'high': [],
                'low': [],
                'close': [],
                'volume': [],
                'cycles': {},
                'crossings': []
            }
    
    def generate_plot_image(self, symbol, data, cycles, cycle_states, as_base64=True):
        """
        Generate plot image for a symbol
        
        Args:
            symbol: Symbol
            data: DataFrame or plot data dictionary
            cycles: Detected cycles
            cycle_states: Cycle states
            as_base64: Whether to return base64 encoded image
            
        Returns:
            Base64 encoded image string or path to saved image
        """
        try:
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})
            
            # Process data
            if isinstance(data, dict):
                # Data is already processed plot data
                plot_data = data
                
                dates = plot_data['dates']
                x_values = np.arange(len(dates))
                
                # Plot price
                if all(k in plot_data for k in ['open', 'high', 'low', 'close']):
                    # Plot OHLC
                    ax1.plot(x_values, plot_data['close'], color='black', linewidth=1.5, label='Close')
                else:
                    # Plot line chart
                    ax1.plot(x_values, plot_data['close'], color='black', linewidth=1.5, label='Price')
                
                # Plot FLDs
                for cycle, cycle_data in plot_data['cycles'].items():
                    cycle = int(cycle)
                    color = cycle_data['color']
                    fld_values = cycle_data['fld']
                    
                    ax1.plot(x_values, fld_values, 
                             label=f'FLD {cycle}', 
                             color=color, linewidth=1.5, alpha=0.8, linestyle='--')
                    
                    # Plot synthetic wave if available
                    if 'wave' in cycle_data:
                        wave_values = cycle_data['wave']
                        # Align to the end of the chart
                        wave_x = x_values[-len(wave_values):]
                        
                        ax1.plot(wave_x, wave_values, 
                                 color=color, linewidth=1, alpha=0.5, linestyle='-')
                
                # Plot crossings
                for crossing in plot_data['crossings']:
                    x_idx = crossing['index']
                    y_val = crossing['price']
                    cycle = crossing['cycle']
                    marker = '^' if crossing['type'] == 'bullish' else 'v'
                    color = next((d['color'] for c, d in plot_data['cycles'].items() 
                                 if int(c) == cycle), 'blue')
                    
                    ax1.plot(x_idx, y_val, marker, 
                             color=color, markersize=10, alpha=0.8)
                
                # X-axis ticks
                tick_indices = np.linspace(0, len(dates)-1, min(10, len(dates))).astype(int)
                ax1.set_xticks(tick_indices)
                ax1.set_xticklabels([dates[i] for i in tick_indices], rotation=45)
                
            else:
                # Data is a DataFrame
                # Last 250 bars for visualization
                visible_bars = min(250, len(data))
                plot_data = data.iloc[-visible_bars:].copy()
                
                # Plot price
                ax1.plot(plot_data.index, plot_data['close'], color='black', linewidth=1.5, label='Close')
                
                # Plot FLDs for each cycle
                for cycle in cycles:
                    cycle = int(cycle)
                    
                    # Calculate FLD
                    fld_period = int(cycle / 2) + 1
                    fld_name = f'fld_{cycle}'
                    data[fld_name] = calculate_fld(data, cycle)
                    
                    # Plot FLD
                    color = self._get_cycle_color(cycle)
                    ax1.plot(plot_data.index, data[fld_name].iloc[-visible_bars:], 
                             label=f'FLD {cycle}', 
                             color=color, linewidth=1.5, alpha=0.8, linestyle='--')
            
            # Add cycle status text
            status_text = "Cycle Status: "
            for cycle, state in cycle_states.items():
                direction = "↑" if state['bullish'] else "↓"
                status_text += f"{cycle}:{direction} "
            
            ax1.text(0.02, 0.02, status_text, transform=ax1.transAxes, fontsize=10,
                     bbox=dict(facecolor='white', alpha=0.7))
            
            # Configure main chart
            ax1.set_title(f"{symbol} - Fibonacci Cycle Analysis")
            ax1.set_ylabel("Price")
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='upper left')
            
            # Plot signals in bottom panel
            if isinstance(data, pd.DataFrame):
                # Calculate signal lines
                for cycle in cycles:
                    cycle = int(cycle)
                    fld_name = f'fld_{cycle}'
                    
                    if fld_name in data.columns:
                        # Calculate signal
                        signal_name = f'signal_{cycle}'
                        data[signal_name] = 0
                        data.loc[(data['close'].shift(1) < data[fld_name].shift(1)) & 
                                 (data['close'] > data[fld_name]), signal_name] = 1
                        data.loc[(data['close'].shift(1) > data[fld_name].shift(1)) & 
                                 (data['close'] < data[fld_name]), signal_name] = -1
                        
                        # Plot as step function
                        color = self._get_cycle_color(cycle)
                        ax2.step(plot_data.index, data[signal_name].iloc[-visible_bars:], 
                                where='post', color=color, linewidth=1.5,
                                label=f'Cycle {cycle}')
            
            # Configure signal panel
            ax2.set_ylabel("Signal")
            ax2.grid(True, alpha=0.3)
            ax2.legend(loc='upper left')
            
            # Format dates
            fig.autofmt_xdate()
            plt.tight_layout()
            
            if as_base64:
                # Save to in-memory buffer
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=100)
                buffer.seek(0)
                
                # Convert to base64
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                plt.close(fig)
                return image_base64
            else:
                # Save to file
                os.makedirs(self.output_dir, exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(self.output_dir, f"{symbol}_{timestamp}.png")
                plt.savefig(filename, dpi=100)
                plt.close(fig)
                
                # Also save to Google Drive if available
                try:
                    from integration.google_drive_integration import drive_storage
                    
                    if os.path.exists(drive_storage.base_path):
                        drive_file = drive_storage.save_file(filename, "charts")
                        logger.info(f"Saved chart to Google Drive: {drive_file}")
                except Exception as e:
                    logger.error(f"Error saving chart to Google Drive: {e}")
                
                return filename
                
        except Exception as e:
            logger.error(f"Error generating plot image: {e}")
            return None    
    def _get_cycle_color(self, cycle):
        """Get color for a cycle"""
        colors = {
            20: '#1f77b4',  # blue
            21: '#1f77b4',  # blue (same as 20)
            34: '#ff7f0e',  # orange
            55: '#2ca02c',  # green
            89: '#d62728',  # red
            144: '#9467bd',  # purple
            233: '#8c564b'   # brown
        }
        
        return colors.get(cycle, '#7f7f7f')  # default gray