```python
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
            if self.data['low'].iloc[idx] <= stop_price:
                return True, stop_price
        else:  # sell
            if self.data['high'].iloc[idx] >= stop_price:
                return True, stop_price
        
        return False, stop_price
    
    def _check_take_profit(self, idx, position):
        """
        Check if take profit has been hit
        
        Args:
            idx: Data index
            position: Current position dictionary
            
        Returns:
            Tuple of (target_hit, target_price)
        """
        target_price = position['take_profit']
        
        # Check if price has hit the target
        if position['type'] == 'buy':
            if self.data['high'].iloc[idx] >= target_price:
                return True, target_price
        else:  # sell
            if self.data['low'].iloc[idx] <= target_price:
                return True, target_price
        
        return False, target_price
```

### 3.5 Machine Learning Signal Enhancement

```python
class MLSignalEnhancer:
    """
    Machine learning-based signal enhancer
    Uses historical data to build a model that can filter out false signals
    """
    
    def __init__(self, min_samples=100):
        """
        Initialize the ML Signal Enhancer
        
        Args:
            min_samples: Minimum samples required before making predictions
        """
        self.min_samples = min_samples
        self.model = None
        self.scaler = None
        self.training_data = []
        self.has_been_trained = False
    
    def add_signal(self, signal_data, outcome):
        """
        Add a signal and its outcome to the training data
        
        Args:
            signal_data: Dictionary with signal features
            outcome: Boolean indicating if the signal was profitable
        """
        # Convert signal data to a flat feature list
        features = self._extract_features(signal_data)
        
        # Add to training data
        self.training_data.append((features, 1 if outcome else 0))
        
        # Train or update model if enough data
        if len(self.training_data) >= self.min_samples and not self.has_been_trained:
            self._train_model()
        elif len(self.training_data) >= self.min_samples and len(self.training_data) % 20 == 0:
            # Retrain every 20 new samples
            self._train_model()
    
    def predict_signal_quality(self, signal_data):
        """
        Predict the quality of a signal
        
        Args:
            signal_data: Dictionary with signal features
            
        Returns:
            Float between 0 and 1 indicating signal quality (higher is better)
        """
        if not self.has_been_trained:
            # Return neutral if not trained
            return 0.5
        
        # Extract features
        features = self._extract_features(signal_data)
        
        # Scale features
        scaled_features = self.scaler.transform([features])
        
        # Make prediction
        try:
            # Get probability of positive outcome
            proba = self.model.predict_proba(scaled_features)[0][1]
            return proba
        except:
            # Fallback if model doesn't support probabilities
            prediction = self.model.predict(scaled_features)[0]
            return float(prediction)
    
    def _extract_features(self, signal_data):
        """
        Extract features from signal data
        
        Args:
            signal_data: Dictionary with signal features
            
        Returns:
            List of numerical features
        """
        features = []
        
        # Cycle information
        features.append(len(signal_data.get('cycles', [])))
        
        # Add cycle powers
        for power in signal_data.get('powers', [])[:3]:  # Use top 3 powers
            features.append(float(power))
        
        # Pad if less than 3 powers
        while len(features) < 4:  # 1 for cycle count + 3 for powers
            features.append(0.0)
        
        # Cycle states
        cycle_states = signal_data.get('cycle_states', {})
        
        # Count bullish/bearish cycles
        bullish_count = sum(1 for state in cycle_states.values() if state.get('bullish', False))
        bearish_count = sum(1 for state in cycle_states.values() if not state.get('bullish', True))
        
        features.append(bullish_count)
        features.append(bearish_count)
        
        # Count recent crossings
        crossover_count = sum(1 for state in cycle_states.values() if state.get('recent_crossover', False))
        crossunder_count = sum(1 for state in cycle_states.values() if state.get('recent_crossunder', False))
        
        features.append(crossover_count)
        features.append(crossunder_count)
        
        # Signal strength
        features.append(float(signal_data.get('combined_strength', 0)))
        
        # Market context
        market_regime = signal_data.get('market_regime', {})
        
        # Trend strength (0-100)
        features.append(float(market_regime.get('trend_strength', 0)))
        
        # Volatility (0-1 range typically)
        features.append(float(market_regime.get('volatility', 0)))
        
        # Range width (0-1 range typically)
        features.append(float(market_regime.get('range_width', 0)))
        
        # Volume data
        features.append(float(signal_data.get('relative_volume', 1.0)))
        
        return features
    
    def _train_model(self):
        """Train the machine learning model on collected data"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
            
            # Prepare data
            X = [data[0] for data in self.training_data]
            y = [data[1] for data in self.training_data]
            
            # Scale features
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Train model
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.model.fit(X_scaled, y)
            
            self.has_been_trained = True
            logger.info(f"ML Signal Enhancer trained on {len(self.training_data)} samples")
            
        except Exception as e:
            logger.error(f"Error training ML model: {e}")
            self.has_been_trained = False
```

## 4. Integration Layer Components

### 4.1 Telegram Bot Enhancement

```python
class EnhancedTelegramBot:
    """
    Enhanced Telegram bot with more advanced features
    """
    
    def __init__(self, token, chat_id, scanner):
        """
        Initialize the enhanced Telegram bot
        
        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID
            scanner: FibCycleScanner instance
        """
        self.token = token
        self.chat_id = chat_id
        self.scanner = scanner
        self.application = None
        self.bot = None
        self.running = False
        
        # Initialize if valid token
        if token and token != 'YOUR_TELEGRAM_BOT_TOKEN' and chat_id:
            try:
                # Initialize bot
                from telegram import Bot, Update
                from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
                
                self.bot = Bot(token)
                
                # Create application
                self.application = Application.builder().token(token).build()
                
                # Add handlers
                self.application.add_handler(CommandHandler("start", self._start_command))
                self.application.add_handler(CommandHandler("help", self._help_command))
                self.application.add_handler(CommandHandler("scan", self._scan_command))
                self.application.add_handler(CommandHandler("analyze", self._analyze_command))
                self.application.add_handler(CommandHandler("market", self._market_command))
                self.application.add_handler(CommandHandler("report", self._report_command))
                self.application.add_handler(CommandHandler("backtest", self._backtest_command))
                
                # Start the bot
                self._start_polling()
                
                logger.info("Enhanced Telegram bot initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
    
    def _start_polling(self):
        """Start the bot polling in a background thread"""
        import threading
        import asyncio
        
        def run_bot():
            # Create event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Start polling
            self.running = True
            loop.run_until_complete(self.application.run_polling(allowed_updates=Update.ALL_TYPES))
        
        # Start in background thread
        self.bot_thread = threading.Thread(target=run_bot)
        self.bot_thread.daemon = True
        self.bot_thread.start()
    
    def stop_bot(self):
        """Stop the bot polling"""
        if self.running and self.application:
            import asyncio
            
            # Get the event loop
            loop = asyncio.get_event_loop()
            
            # Stop the application
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.application.stop(), loop)
            
            self.running = False
            logger.info("Telegram bot stopped")
    
    async def _start_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE'):
        """Handle /start command"""
        user = update.effective_user
        await update.message.reply_text(
            f"Hello {user.first_name}! I'm your Fibonacci Cycle Scanner bot.\n\n"
            f"Use /help to see available commands."
        )
    
    async def _help_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE'):
        """Handle /help command"""
        help_text = (
            "*Fibonacci Cycle Scanner Commands*\n\n"
            "*/scan SYMBOL [INTERVAL]* - Scan a single symbol\n"
            "Example: `/scan RELIANCE daily`\n\n"
            "*/analyze SYMBOL INTERVAL* - Detailed symbol analysis\n"
            "Example: `/analyze INFY daily`\n\n"
            "*/market* - Overall market analysis\n\n"
            "*/report [INTERVAL]* - Get latest scan report\n"
            "Example: `/report daily`\n\n"
            "*/backtest SYMBOL DAYS* - Run a quick backtest\n"
            "Example: `/backtest HDFC 90`\n\n"
            "Available intervals: weekly, daily, 4h, 1h, 15min, 5min"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def _scan_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE'):
        """Handle /scan command"""
        if not self.scanner:
            await update.message.reply_text("Scanner not available")
            return
        
        # Get arguments
        args = context.args
        if not args:
            await update.message.reply_text("Please provide a symbol to scan. Example: /scan RELIANCE")
            return
        
        symbol = args[0].upper()
        interval = args[1].lower() if len(args) > 1 else "daily"
        
        # Validate interval
        valid_intervals = ["weekly", "daily", "4h", "1h", "15min", "5min"]
        if interval not in valid_intervals:
            await update.message.reply_text(
                f"Invalid interval. Please use one of: {', '.join(valid_intervals)}"
            )
            return
        
        # Send initial response
        message = await update.message.reply_text(f"Scanning {symbol} on {interval} timeframe...")
        
        try:
            # Run the scan
            from concurrent.futures import ThreadPoolExecutor
            
            def run_analysis():
                from fib_cycle_scanner import ScanParameters
                params = ScanParameters(lookback=5000)
                return self.scanner.analyze_symbol(symbol, interval, params)
            
            # Run in thread pool
            with ThreadPoolExecutor() as executor:
                future = executor.submit(run_analysis)
                result = future.result()
            
            if result is None:
                await message.edit_text(f"No data available for {symbol}")
                return
            
            # Format the result
            response = f"*{symbol} - {interval.upper()} Analysis*\n\n"
            response += f"*Signal:* {result.signal}\n"
            response += f"*Confidence:* {result.confidence}\n"
            response += f"*Strength:* {result.combined_strength:.2f}\n"
            
            # Add cycles information
            if hasattr(result, 'cycles') and result.cycles:
                response += f"*Key Cycles:* {', '.join(str(c) for c in result.cycles)}\n\n"
            
            # Add entry/exit recommendations
            if "Buy" in result.signal:
                response += "*Entry Strategy:* Enter long on a pullback to the 21-period FLD\n"
                response += "*Exit Strategy:* Exit when price crosses below the 21-period FLD\n"
            elif "Sell" in result.signal:
                response += "*Entry Strategy:* Enter short on a rally to the 21-period FLD\n"
                response += "*Exit Strategy:* Exit when price crosses above the 21-period FLD\n"
            else:
                response += "*Strategy:* Wait for clearer signals\n"
            
            # Send the analysis
            await message.edit_text(response, parse_mode="Markdown")
            
            # Generate and send chart image
            self._send_chart_image(result, update)
            
        except Exception as e:
            logger.error(f"Error in scan command: {e}")
            await message.edit_text(f"Error analyzing {symbol}: {str(e)}")
    
    async def _analyze_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE'):
        """Handle /analyze command for detailed multi-timeframe analysis"""
        if not self.scanner:
            await update.message.reply_text("Scanner not available")
            return
        
        # Get arguments
        args = context.args
        if len(args) < 1:
            await update.message.reply_text("Please provide a symbol. Example: /analyze RELIANCE")
            return
        
        symbol = args[0].upper()
        
        # Send initial response
        message = await update.message.reply_text(f"Performing detailed analysis of {symbol}...")
        
        try:
            # Run multi-timeframe analysis
            from concurrent.futures import ThreadPoolExecutor
            
            def run_analysis():
                timeframes = ["daily", "4h", "1h", "15min"]
                return analyze_multi_timeframe(symbol, timeframes)
            
            # Run in thread pool
            with ThreadPoolExecutor() as executor:
                future = executor.submit(run_analysis)
                result = future.result()
            
            if result is None:
                await message.edit_text(f"No data available for {