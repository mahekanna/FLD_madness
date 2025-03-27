import numpy as np
import pandas as pd
import talib
from scipy import signal
from scipy.fft import fft
import logging

logger = logging.getLogger(__name__)

# Try importing GPU libraries
try:
    import cupy as cp
    HAS_GPU = True
    logger.info("GPU acceleration available with CuPy")
except ImportError:
    cp = np
    HAS_GPU = False
    logger.info("GPU libraries not found, using CPU mode")

def detect_cycles(data, min_periods=20, max_periods=250, num_cycles=3, use_gpu=False):
    """
    Detect dominant cycles in price data using FFT
    
    Args:
        data: DataFrame or Series with price data
        min_periods: Minimum cycle length to detect
        max_periods: Maximum cycle length to detect
        num_cycles: Number of cycles to return
        use_gpu: Whether to use GPU acceleration if available
        
    Returns:
        Tuple of (detected_cycles, cycle_powers)
    """
    try:
        # If data is a DataFrame, extract the closing prices
        if isinstance(data, pd.DataFrame):
            if 'close' in data.columns:
                series = data['close']
            elif 'Close' in data.columns:
                series = data['Close']
            else:
                # Try to use a price average
                if all(col in data.columns for col in ['high', 'low', 'close']):
                    series = (data['high'] + data['low'] + data['close']) / 3
                else:
                    # Just use the first column as a fallback
                    series = data.iloc[:, 0]
        else:
            series = data
            
        # Remove NaN values
        clean_series = series.dropna()
        
        # Apply simple detrending using a long EMA
        detrended = clean_series - talib.EMA(clean_series, timeperiod=len(clean_series)//4)
        
        # Apply FFT to find dominant cycles
        if use_gpu and HAS_GPU:
            # Use GPU for FFT computation
            d_detrended = cp.asarray(detrended.values)
            fft_values = cp.abs(cp.fft.fft(d_detrended))
            freqs = cp.fft.fftfreq(len(d_detrended))
            # Transfer back to CPU for further processing
            fft_values = cp.asnumpy(fft_values)
            freqs = cp.asnumpy(freqs)
        else:
            # Use CPU for FFT computation
            fft_values = np.abs(fft(detrended.values))
            freqs = np.fft.fftfreq(len(detrended))
        
        # Only look at positive frequencies and within our range of interest
        positive_freqs_idx = np.where((freqs > 0) & 
                                      (freqs < 1/min_periods) & 
                                      (freqs > 1/max_periods))[0]
        
        # Sort by magnitude to find dominant cycles
        sorted_idx = np.argsort(fft_values[positive_freqs_idx])[::-1]
        dominant_periods = np.round(1/freqs[positive_freqs_idx][sorted_idx[:num_cycles*2]]).astype(int)
        
        # Get powers (magnitudes) of the dominant cycles
        powers = fft_values[positive_freqs_idx][sorted_idx[:num_cycles*2]]
        # Normalize powers
        if len(powers) > 0:
            powers = powers / np.max(powers)
            
        # Make sure dominant periods are within expected range and unique
        filtered_periods = []
        filtered_powers = []
        seen_periods = set()
        
        for i, period in enumerate(dominant_periods):
            if min_periods <= period <= max_periods and period not in seen_periods:
                filtered_periods.append(period)
                filtered_powers.append(powers[i])
                seen_periods.add(period)
        
        # Convert to numpy arrays
        filtered_periods = np.array(filtered_periods)
        filtered_powers = np.array(filtered_powers)
        
        # If we didn't find enough cycles, add some Fibonacci-related ones
        if len(filtered_periods) < num_cycles:
            additional_periods = [21, 34, 55, 89, 144, 233]
            for period in additional_periods:
                if period not in filtered_periods and len(filtered_periods) < num_cycles:
                    filtered_periods = np.append(filtered_periods, period)
                    # Assign a lower power to added cycles
                    filtered_powers = np.append(filtered_powers, 0.5)
        
        # Return only the requested number of cycles
        return filtered_periods[:num_cycles], filtered_powers[:num_cycles]
        
    except Exception as e:
        logger.error(f"Error detecting cycles: {e}")
        # Fallback to Fibonacci cycles
        return np.array([21, 34, 55]), np.array([0.8, 0.9, 0.7])

def detect_cycle_extremes(series, cycle_length):
    """
    Detect peaks and troughs in a price series based on cycle length
    
    Args:
        series: Price series
        cycle_length: Length of the cycle to detect extremes for
        
    Returns:
        Tuple of (peaks, troughs, peak_properties, trough_properties)
    """
    try:
        # Use peak detection to find local maxima and minima
        prominence = np.std(series) * 0.5  # Dynamic prominence based on volatility
        distance = int(cycle_length * 0.6)  # Allow some flexibility in peak spacing
        
        # Find peaks (tops)
        peaks, peak_properties = signal.find_peaks(series, distance=distance, prominence=prominence)
        
        # Find troughs (bottoms)
        inverted = -series
        troughs, trough_properties = signal.find_peaks(inverted, distance=distance, prominence=prominence)
        
        return peaks, troughs, peak_properties, trough_properties
        
    except Exception as e:
        logger.error(f"Error detecting cycle extremes: {e}")
        return [], [], {}, {}

def generate_cycle_wave(length, num_points, phase_shift=0):
    """
    Generate synthetic cycle wave based on cycle length
    
    Args:
        length: Cycle length
        num_points: Number of points to generate
        phase_shift: Phase shift in radians
        
    Returns:
        NumPy array with synthetic cycle wave
    """
    try:
        # Create a sine wave with the specified cycle length
        x = np.linspace(0, 2 * np.pi * (num_points / length), num_points)
        return np.sin(x + phase_shift)
        
    except Exception as e:
        logger.error(f"Error generating cycle wave: {e}")
        return np.zeros(num_points)