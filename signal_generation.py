import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def calculate_combined_strength(cycle_states):
    """
    Calculate combined signal strength from cycle states
    
    Args:
        cycle_states: Dictionary of cycle states by cycle length
        
    Returns:
        Float value indicating combined signal strength (positive for bullish, negative for bearish)
    """
    try:
        if not cycle_states:
            return 0
        
        combined_strength = 0
        
        for cycle, state in cycle_states.items():
            # Weight larger cycles more heavily
            cycle_weight = 1.0
            if cycle == 34:
                cycle_weight = 1.5  # 34-period cycle (Fibonacci) gets higher weight
            elif cycle > 34:
                cycle_weight = 2.0  # Larger cycles get even higher weight
            
            # Add contribution from current state
            direction = 1 if state['bullish'] else -1
            combined_strength += state['power'] * direction * cycle_weight
            
            # Add bonus for recent crossings
            if state['recent_crossover']:
                combined_strength += 0.5 * cycle_weight
            if state['recent_crossunder']:
                combined_strength -= 0.5 * cycle_weight
        
        # Normalize by number of cycles
        if cycle_states:
            combined_strength /= len(cycle_states)
        
        return combined_strength
        
    except Exception as e:
        logger.error(f"Error calculating combined strength: {e}")
        return 0

def determine_signal(cycle_states, combined_strength):
    """
    Determine trading signal based on cycle states and combined strength
    
    Args:
        cycle_states: Dictionary of cycle states by cycle length
        combined_strength: Combined signal strength value
        
    Returns:
        Tuple of (signal, confidence)
    """
    try:
        if not cycle_states:
            return "Neutral", "Low"
        
        # Count bullish and bearish cycles
        bullish_cycles = sum(1 for state in cycle_states.values() if state['bullish'])
        bearish_cycles = len(cycle_states) - bullish_cycles
        
        # Count recent crossings
        recent_bullish = sum(1 for state in cycle_states.values() if state['recent_crossover'])
        recent_bearish = sum(1 for state in cycle_states.values() if state['recent_crossunder'])
        
        # Check if 34-cycle is present (primary trend cycle)
        cycle_34_bullish = False
        if 34 in cycle_states:
            cycle_34_bullish = cycle_states[34]['bullish']
        
        # Determine signal based on combined strength
        if combined_strength > 1.5:
            signal = "Strong Buy"
        elif combined_strength > 0.8:
            signal = "Buy"
        elif combined_strength > 0.3:
            signal = "Weak Buy"
        elif combined_strength < -1.5:
            signal = "Strong Sell"
        elif combined_strength < -0.8:
            signal = "Sell"
        elif combined_strength < -0.3:
            signal = "Weak Sell"
        else:
            signal = "Neutral"
        
        # Determine confidence
        if abs(combined_strength) > 1.5:
            confidence = "High"
        elif abs(combined_strength) > 0.8:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        # Upgrade signal if all cycles aligned with recent crossings
        if bullish_cycles == len(cycle_states) and recent_bullish > 0:
            signal = "Strong Buy"
            confidence = "High"
        elif bearish_cycles == len(cycle_states) and recent_bearish > 0:
            signal = "Strong Sell"
            confidence = "High"
        
        # Special case for 34-cycle alignment
        if 34 in cycle_states:
            if cycle_34_bullish and "Buy" in signal:
                confidence = max(confidence, "Medium")  # At least medium confidence if 34-cycle aligns
            elif not cycle_34_bullish and "Sell" in signal:
                confidence = max(confidence, "Medium")  # At least medium confidence if 34-cycle aligns
        
        return signal, confidence
        
    except Exception as e:
        logger.error(f"Error determining signal: {e}")
        return "Neutral", "Low"

def generate_position_guidance(signal, confidence, last_price, cycle_states):
    """
    Generate position guidance based on signal and cycle states
    
    Args:
        signal: Trading signal
        confidence: Signal confidence
        last_price: Last price
        cycle_states: Dictionary of cycle states by cycle length
    
    Returns:
        Dictionary with position guidance
    """
    try:
        # Initialize guidance
        guidance = {
            'action': 'Hold',
            'entry_strategy': '',
            'exit_strategy': '',
            'stop_loss': None,
            'target': None,
            'position_size': 0,
            'timeframe': 'Medium-term'
        }
        
        # Set action based on signal
        if "Buy" in signal:
            guidance['action'] = 'Buy'
        elif "Sell" in signal:
            guidance['action'] = 'Sell'
        
        # Position size based on confidence
        if confidence == "High":
            guidance['position_size'] = 1.0  # Full position
        elif confidence == "Medium":
            guidance['position_size'] = 0.5  # Half position
        elif confidence == "Low":
            guidance['position_size'] = 0.25  # Quarter position
        
        # Entry strategy
        if "Buy" in signal:
            guidance['entry_strategy'] = "Enter long on a pullback to the 21-period FLD."
            if 34 in cycle_states and cycle_states[34]['bullish']:
                guidance['entry_strategy'] += " Confirmed by 34-period cycle."
        elif "Sell" in signal:
            guidance['entry_strategy'] = "Enter short on a rally to the 21-period FLD."
            if 34 in cycle_states and not cycle_states[34]['bullish']:
                guidance['entry_strategy'] += " Confirmed by 34-period cycle."
        
        # Exit strategy
        if "Buy" in signal:
            guidance['exit_strategy'] = "Exit when price crosses below the 21-period FLD or at the projected cycle top."
        elif "Sell" in signal:
            guidance['exit_strategy'] = "Exit when price crosses above the 21-period FLD or at the projected cycle bottom."
        
        # Stop loss and targets - rough estimates based on cycle lengths
        avg_cycle_length = np.mean([cycle for cycle in cycle_states.keys()])
        volatility_factor = 0.02  # 2% default
        
        if "Buy" in signal:
            guidance['stop_loss'] = round(last_price * (1 - volatility_factor), 2)
            guidance['target'] = round(last_price * (1 + volatility_factor * 2), 2)  # 2:1 reward/risk
        elif "Sell" in signal:
            guidance['stop_loss'] = round(last_price * (1 + volatility_factor), 2)
            guidance['target'] = round(last_price * (1 - volatility_factor * 2), 2)  # 2:1 reward/risk
        
        # Timeframe based on dominant cycles
        if np.any([cycle > 50 for cycle in cycle_states.keys()]):
            guidance['timeframe'] = 'Long-term'
        elif np.any([cycle > 20 for cycle in cycle_states.keys()]):
            guidance['timeframe'] = 'Medium-term'
        else:
            guidance['timeframe'] = 'Short-term'
        
        return guidance
        
    except Exception as e:
        logger.error(f"Error generating position guidance: {e}")
        return {
            'action': 'Hold',
            'entry_strategy': 'Insufficient data for recommendations',
            'exit_strategy': 'Insufficient data for recommendations',
            'stop_loss': None,
            'target': None,
            'position_size': 0,
            'timeframe': 'Unknown'
        }