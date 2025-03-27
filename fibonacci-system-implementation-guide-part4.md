```python
class FLDCrossoverStrategy:
    """FLD Crossover trading strategy for backtesting"""
    
    def __init__(self, data, params, stop_loss_type="atr", 
                take_profit_type="next_cycle", position_sizing="fixed"):
        """
        Initialize FLD Crossover strategy
        
        Args:
            data: DataFrame with historical price data
            params: ScanParameters object
            stop_loss_type: Stop loss method
            take_profit_type: Take profit method
            position_sizing: Position sizing method
        """
        self.data = data.copy()
        self.params = params
        self.stop_loss_type = stop_loss_type
        self.take_profit_type = take_profit_type
        self.position_sizing = position_sizing
        
        # Prepare data for backtesting
        self._prepare_data()
        
    def _prepare_data(self):
        """Prepare data for backtesting by adding indicators"""
        # Detect dominant cycles
        all_cycles, all_powers, fib_cycles, fib_powers = detect_cycles(self.data, self.params)
        self.cycles = fib_cycles
        
        # Calculate FLDs for each cycle
        for cycle in self.cycles:
            # Calculate FLD
            fld_period = int(cycle / 2) + 1
            fld_name = f'fld_{cycle}'
            self.data[fld_name] = talib.EMA(self.data['close'].values, timeperiod=fld_period)
            
            # Calculate FLD crossover signals
            signal_name = f'signal_{cycle}'
            self.data[signal_name] = 0
            
            # Bullish crossover: 1
            self.data.loc[(self.data['close'].shift(1) < self.data[fld_name].shift(1)) & 
                           (self.data['close'] > self.data[fld_name]), signal_name] = 1
                           
            # Bearish crossover: -1
            self.data.loc[(self.data['close'].shift(1) > self.data[fld_name].shift(1)) & 
                           (self.data['close'] < self.data[fld_name]), signal_name] = -1
        
        # Add ATR for stop loss calculations
        self.data['atr'] = talib.ATR(
            self.data['high'].values, 
            self.data['low'].values, 
            self.data['close'].values, 
            timeperiod=14
        )
        
        # Create composite signal
        self.data['composite_signal'] = 0
        for cycle in self.cycles:
            signal_name = f'signal_{cycle}'
            self.data['composite_signal'] += self.data[signal_name]
    
    def run(self):
        """
        Run the backtest
        
        Returns:
            Tuple of (trades, equity_curve)
        """
        # Initialize variables
        equity = 1.0
        position = None
        trades = []
        equity_curve = []
        
        # Iterate through data (skip the beginning to have enough data for indicators)
        start_idx = max(50, int(max(self.cycles)))
        
        for i in range(start_idx, len(self.data)):
            date = self.data.index[i]
            
            # Track equity
            equity_curve.append({
                'date': date,
                'equity': equity
            })
            
            # Check for exit if in a position
            if position is not None:
                # Check stop loss
                stop_hit, stop_price = self._check_stop_loss(i, position)
                
                # Check take profit
                target_hit, target_price = self._check_take_profit(i, position)
                
                # Check for exit signal
                exit_signal = self._check_exit_signal(i, position)
                
                # Exit condition
                if stop_hit or target_hit or exit_signal:
                    # Calculate profit/loss
                    exit_price = self.data['close'].iloc[i]
                    
                    if stop_hit:
                        exit_price = stop_price
                        exit_reason = "stop_loss"
                    elif target_hit:
                        exit_price = target_price
                        exit_reason = "take_profit"
                    else:
                        exit_reason = "signal"
                    
                    # Calculate profit percentage
                    if position['type'] == 'buy':
                        profit_pct = (exit_price / position['entry_price']) - 1
                    else:  # sell
                        profit_pct = 1 - (exit_price / position['entry_price'])
                    
                    # Update equity
                    equity *= (1 + profit_pct * position['size'])
                    
                    # Record trade
                    position['exit_date'] = date
                    position['exit_price'] = exit_price
                    position['exit_reason'] = exit_reason
                    position['profit_pct'] = profit_pct
                    position['equity'] = equity
                    
                    trades.append(position)
                    
                    # Reset position
                    position = None
            
            # Check for entry if not in a position
            if position is None:
                entry_signal, trade_type = self._check_entry_signal(i)
                
                if entry_signal:
                    # Calculate position size
                    size = self._calculate_position_size(i, trade_type, equity)
                    
                    # Record entry
                    entry_price = self.data['close'].iloc[i]
                    position = {
                        'type': trade_type,
                        'entry_date': date,
                        'entry_price': entry_price,
                        'size': size,
                        'stop_loss': self._calculate_stop_loss(i, trade_type, entry_price),
                        'take_profit': self._calculate_take_profit(i, trade_type, entry_price)
                    }
        
        # Close any open position at the end
        if position is not None:
            # Calculate profit/loss
            exit_price = self.data['close'].iloc[-1]
            
            if position['type'] == 'buy':
                profit_pct = (exit_price / position['entry_price']) - 1
            else:  # sell
                profit_pct = 1 - (exit_price / position['entry_price'])
            
            # Update equity
            equity *= (1 + profit_pct * position['size'])
            
            # Record trade
            position['exit_date'] = self.data.index[-1]
            position['exit_price'] = exit_price
            position['exit_reason'] = "end_of_data"
            position['profit_pct'] = profit_pct
            position['equity'] = equity
            
            trades.append(position)
        
        # Convert equity curve to DataFrame
        equity_df = pd.DataFrame(equity_curve).set_index('date')
        
        return trades, equity_df
    
    def _check_entry_signal(self, idx):
        """
        Check for entry signal at the given index
        
        Args:
            idx: Data index
            
        Returns:
            Tuple of (entry_signal, trade_type)
        """
        # Get composite signal
        composite = self.data['composite_signal'].iloc[idx]
        
        # Check primary cycle signal (usually cycle 34)
        primary_cycle = max(self.cycles) if len(self.cycles) > 0 else 34
        primary_signal = self.data[f'signal_{primary_cycle}'].iloc[idx]
        
        # Check for strong signal (multi-cycle agreement)
        if composite >= 2 and primary_signal > 0:
            return True, 'buy'
        elif composite <= -2 and primary_signal < 0:
            return True, 'sell'
        
        return False, None
    
    def _check_exit_signal(self, idx, position):
        """
        Check for exit signal at the given index
        
        Args:
            idx: Data index
            position: Current position dictionary
            
        Returns:
            Boolean indicating exit signal
        """
        # Get composite signal
        composite = self.data['composite_signal'].iloc[idx]
        
        # Check for opposing signal
        if position['type'] == 'buy' and composite <= -1:
            return True
        elif position['type'] == 'sell' and composite >= 1:
            return True
        
        return False
    
    def _calculate_stop_loss(self, idx, trade_type, entry_price):
        """
        Calculate stop loss price
        
        Args:
            idx: Data index
            trade_type: Trade type ('buy' or 'sell')
            entry_price: Entry price
            
        Returns:
            Stop loss price
        """
        if self.stop_loss_type == "atr":
            # ATR-based stop loss
            atr = self.data['atr'].iloc[idx]
            atr_multiplier = 2.0
            
            if trade_type == 'buy':
                return entry_price - (atr * atr_multiplier)
            else:  # sell
                return entry_price + (atr * atr_multiplier)
                
        elif self.stop_loss_type == "cycle_extreme":
            # Use previous cycle extreme
            lookback = int(max(self.cycles) * 0.5)
            if trade_type == 'buy':
                # Find recent low
                recent_low = self.data['low'].iloc[max(0, idx-lookback):idx+1].min()
                return recent_low * 0.99  # Slight buffer
            else:  # sell
                # Find recent high
                recent_high = self.data['high'].iloc[max(0, idx-lookback):idx+1].max()
                return recent_high * 1.01  # Slight buffer
                
        elif self.stop_loss_type == "percentage":
            # Fixed percentage stop
            stop_percentage = 0.03  # 3%
            
            if trade_type == 'buy':
                return entry_price * (1 - stop_percentage)
            else:  # sell
                return entry_price * (1 + stop_percentage)
        
        else:
            # Default to ATR
            atr = self.data['atr'].iloc[idx]
            atr_multiplier = 2.0
            
            if trade_type == 'buy':
                return entry_price - (atr * atr_multiplier)
            else:  # sell
                return entry_price + (atr * atr_multiplier)
    
    def _calculate_take_profit(self, idx, trade_type, entry_price):
        """
        Calculate take profit price
        
        Args:
            idx: Data index
            trade_type: Trade type ('buy' or 'sell')
            entry_price: Entry price
            
        Returns:
            Take profit price
        """
        if self.take_profit_type == "next_cycle":
            # Project to next cycle extreme
            primary_cycle = max(self.cycles) if len(self.cycles) > 0 else 34
            cycle_projection = primary_cycle  # Full cycle projection
            
            # Calculate projected move using average cycle range
            lookback = min(idx, int(primary_cycle * 3))
            cycle_range = (self.data['high'].iloc[idx-lookback:idx+1].max() - 
                          self.data['low'].iloc[idx-lookback:idx+1].min())
            avg_range_percent = cycle_range / self.data['close'].iloc[idx-lookback]
            
            if trade_type == 'buy':
                return entry_price * (1 + avg_range_percent * 0.8)  # 80% of average range
            else:  # sell
                return entry_price * (1 - avg_range_percent * 0.8)
                
        elif self.take_profit_type == "fib_extension":
            # Fibonacci extension based on recent move
            lookback = int(min(self.cycles) * 0.5) if len(self.cycles) > 0 else 10
            
            if trade_type == 'buy':
                # Find recent swing low and high
                recent_low = self.data['low'].iloc[max(0, idx-lookback):idx+1].min()
                recent_high = self.data['high'].iloc[max(0, idx-lookback):idx+1].max()
                
                # 1.618 extension
                extension = entry_price + (recent_high - recent_low) * 1.618
                return extension
            else:  # sell
                # Find recent swing high and low
                recent_high = self.data['high'].iloc[max(0, idx-lookback):idx+1].max()
                recent_low = self.data['low'].iloc[max(0, idx-lookback):idx+1].min()
                
                # 1.618 extension
                extension = entry_price - (recent_high - recent_low) * 1.618
                return extension
                
        elif self.take_profit_type == "risk_reward":
            # Fixed risk-reward ratio
            risk_reward = 2.0
            
            # Calculate based on stop loss
            if trade_type == 'buy':
                risk = entry_price - self._calculate_stop_loss(idx, trade_type, entry_price)
                return entry_price + (risk * risk_reward)
            else:  # sell
                risk = self._calculate_stop_loss(idx, trade_type, entry_price) - entry_price
                return entry_price - (risk * risk_reward)
        
        else:
            # Default to a fixed percentage
            target_percentage = 0.06  # 6%
            
            if trade_type == 'buy':
                return entry_price * (1 + target_percentage)
            else:  # sell
                return entry_price * (1 - target_percentage)
    
    def _calculate_position_size(self, idx, trade_type, equity):
        """
        Calculate position size
        
        Args:
            idx: Data index
            trade_type: Trade type ('buy' or 'sell')
            equity: Current equity value
            
        Returns:
            Position size as a decimal (0-1)
        """
        if self.position_sizing == "fixed":
            # Fixed percentage of equity
            return 1.0  # 100% of available equity
            
        elif self.position_sizing == "risk_based":
            # Risk a fixed percentage of equity
            risk_percentage = 0.02  # 2% risk
            
            # Calculate position size based on stop loss
            entry_price = self.data['close'].iloc[idx]
            stop_loss = self._calculate_stop_loss(idx, trade_type, entry_price)
            
            if trade_type == 'buy':
                risk_per_unit = entry_price - stop_loss
                if risk_per_unit <= 0:
                    return 0.5  # Default to 50% if invalid risk
                return (equity * risk_percentage) / risk_per_unit
            else:  # sell
                risk_per_unit = stop_loss - entry_price
                if risk_per_unit <= 0:
                    return 0.5  # Default to 50% if invalid risk
                return (equity * risk_percentage) / risk_per_unit
                
        elif self.position_sizing == "kelly":
            # Kelly criterion based on historical win rate and average win/loss
            # Need historical data to calculate
            # Default to a moderate position size for now
            return 0.5
            
        else:
            # Default to fixed
            return 1.0
    
    def _check_stop_loss(self, idx, position):
        """
        Check if stop loss has been hit
        
        Args:
            idx: Data index
            position: Current position dictionary
            
        Returns:
            Tuple of (stop_hit, stop_price)
        """
        stop_price = position['stop_loss']
        
        # Check if price has hit the stop
        if position['type'] == 'buy':
            if self.data['low'].iloc[idx]