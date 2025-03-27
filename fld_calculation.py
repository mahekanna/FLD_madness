import numpy as np
import pandas as pd
import talib
import logging

logger = logging.getLogger(__name__)

def calculate_fld(data, cycle_length):
    """
    Calculate Future Line of Demarcation (FLD) for a given cycle length
    
    Args:
        data: DataFrame with price data
        cycle_length: Cycle length to calculate FLD for
        
    Returns:
        Series with FLD values
    """
    try:
        # Ensure we have price data
        if 'close' not in data.columns:
            logger.warning("No 'close' column found in data. Trying alternative columns.")
            if 'Close' in data.columns:
                close = data['Close']
            else:
                # Use average of available price data
                if all(col in data.columns for col in ['high', 'low', 'close']):
                    close = (data['high'] + data['low'] + data['close']) / 3
                elif all(col in data.columns for col in ['High', 'Low', 'Close']):
                    close = (data['High'] + data['Low'] + data['Close']) / 3
                else:
                    # Just use the first column as a fallback
                    close = data.iloc[:, 0]
        else:
            close = data['close']
        
        # Calculate FLD as EMA with period = (cycle_length / 2) + 1
        fld_period = int(cycle_length / 2) + 1
        
        # Compute the FLD
        fld = talib.EMA(close.values, timeperiod=fld_period)
        
        # Return as Series with original index
        return pd.Series(fld, index=data.index)
        
    except Exception as e:
        logger.error(f"Error calculating FLD for cycle {cycle_length}: {e}")
        return pd.Series(np.nan, index=data.index)

def detect_fld_crossings(data, fld_series, lookback=None):
    """
    Detect price crossings of the FLD
    
    Args:
        data: DataFrame with price data
        fld_series: Series with FLD values
        lookback: Number of periods to look back (None for all data)
        
    Returns:
        DataFrame with crossing information
    """
    try:
        # Ensure we have price data
        if 'close' not in data.columns:
            if 'Close' in data.columns:
                close = data['Close']
            else:
                # Use average of available price data
                if all(col in data.columns for col in ['high', 'low', 'close']):
                    close = (data['high'] + data['low'] + data['close']) / 3
                elif all(col in data.columns for col in ['High', 'Low', 'Close']):
                    close = (data['High'] + data['Low'] + data['Close']) / 3
                else:
                    # Just use the first column as a fallback
                    close = data.iloc[:, 0]
        else:
            close = data['close']
        
        # Limit to lookback period if specified
        if lookback is not None:
            close = close.iloc[-lookback:]
            fld_series = fld_series.iloc[-lookback:]
        
        # Initialize crossing Series
        crossing = pd.Series(np.zeros(len(close)), index=close.index)
        
        # Detect bullish crossings (price crosses above FLD)
        crossing[(close.shift(1) <= fld_series.shift(1)) & (close > fld_series)] = 1
        
        # Detect bearish crossings (price crosses below FLD)
        crossing[(close.shift(1) >= fld_series.shift(1)) & (close < fld_series)] = -1
        
        # Create DataFrame with crossings
        crossings_df = pd.DataFrame({
            'price': close,
            'fld': fld_series,
            'crossing': crossing
        })
        
        # Filter to only include crossings
        crossings_df = crossings_df[crossings_df['crossing'] != 0]
        
        return crossings_df
        
    except Exception as e:
        logger.error(f"Error detecting FLD crossings: {e}")
        return pd.DataFrame()

def calculate_cycle_state(data, cycle_length, fld_series=None, recent_bars=5):
    """
    Calculate the current state of a cycle
    
    Args:
        data: DataFrame with price data
        cycle_length: Cycle length
        fld_series: Precalculated FLD series (optional)
        recent_bars: Number of recent bars to check for crossings
        
    Returns:
        Dictionary with cycle state information
    """
    try:
        # Ensure we have price data
        if 'close' not in data.columns:
            if 'Close' in data.columns:
                close = data['Close']
            else:
                # Use average of available price data
                if all(col in data.columns for col in ['high', 'low', 'close']):
                    close = (data['high'] + data['low'] + data['close']) / 3
                elif all(col in data.columns for col in ['High', 'Low', 'Close']):
                    close = (data['High'] + data['Low'] + data['Close']) / 3
                else:
                    # Just use the first column as a fallback
                    close = data.iloc[:, 0]
        else:
            close = data['close']
        
        # Calculate FLD if not provided
        if fld_series is None:
            fld_series = calculate_fld(data, cycle_length)
        
        # Get latest values
        latest_close = close.iloc[-1]
        latest_fld = fld_series.iloc[-1]
        
        # Determine if price is above or below FLD
        bullish = latest_close > latest_fld
        
        # Check for recent crossings
        recent_close = close.iloc[-recent_bars:]
        recent_fld = fld_series.iloc[-recent_bars:]
        
        # Initialize crossing flags
        recent_crossover = False
        recent_crossunder = False
        
        # Check for crossings in recent bars
        for i in range(1, len(recent_close)):
            # Bullish crossover
            if (recent_close.iloc[i-1] <= recent_fld.iloc[i-1] and 
                recent_close.iloc[i] > recent_fld.iloc[i]):
                recent_crossover = True
            
            # Bearish crossunder
            if (recent_close.iloc[i-1] >= recent_fld.iloc[i-1] and 
                recent_close.iloc[i] < recent_fld.iloc[i]):
                recent_crossunder = True
        
        # Calculate cycle power (strength) based on relationship to FLD
        power = abs(latest_close - latest_fld) / latest_fld
        power = min(power * 100, 1.0)  # Scale and cap power
        
        return {
            'cycle': cycle_length,
            'fld_value': latest_fld,
            'bullish': bullish,
            'recent_crossover': recent_crossover,
            'recent_crossunder': recent_crossunder,
            'power': power
        }
        
    except Exception as e:
        logger.error(f"Error calculating cycle state for cycle {cycle_length}: {e}")
        return {
            'cycle': cycle_length,
            'fld_value': 0,
            'bullish': False,
            'recent_crossover': False,
            'recent_crossunder': False,
            'power': 0
        }