```python
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
                await message.edit_text(f"No data available for {symbol}")
                return
            
            # Format the multi-timeframe analysis
            response = f"*{symbol} - Multi-Timeframe Analysis*\n\n"
            
            # Overall alignment info
            response += f"*Timeframe Alignment:* {result['alignment_score']:.2f} ({result['alignment_direction'].title()})\n"
            response += f"*Composite Signal:* {result['composite_signal']}\n\n"
            
            # Individual timeframe signals
            response += "*Signals by Timeframe:*\n"
            for tf, tf_result in result['timeframe_results'].items():
                signal_icon = "📈" if "Buy" in tf_result.signal else "📉" if "Sell" in tf_result.signal else "⚖️"
                response += f"- {tf.upper()}: {signal_icon} {tf_result.signal} ({tf_result.confidence})\n"
            
            # Trading recommendation
            response += "\n*Trading Recommendation:*\n"
            if "Buy" in result['composite_signal']:
                response += "✅ Look for long entries when price pulls back to the 21-period FLD on the 1h/15min timeframes\n"
            elif "Sell" in result['composite_signal']:
                response += "❌ Look for short entries when price rallies to the 21-period FLD on the 1h/15min timeframes\n"
            else:
                response += "⚠️ No clear directional bias at this time. Wait for stronger alignment.\n"
            
            # Send the analysis
            await message.edit_text(response, parse_mode="Markdown")
            
            # Send chart for the daily timeframe
            daily_result = result['timeframe_results'].get('daily')
            if daily_result:
                self._send_chart_image(daily_result, update)
            
        except Exception as e:
            logger.error(f"Error in analyze command: {e}")
            await message.edit_text(f"Error analyzing {symbol}: {str(e)}")
    
    def _send_chart_image(self, result, update):
        """Generate and send chart image"""
        try:
            import io
            import matplotlib.pyplot as plt
            from PIL import Image
            
            # Generate the chart
            fig = self.scanner.generate_plot_image(
                result.symbol, 
                result.plot_data, 
                result.cycles, 
                result.cycle_states,
                as_base64=False
            )
            
            # Save to buffer
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100)
            plt.close(fig)  # Close to free memory
            
            # Create PIL Image
            buf.seek(0)
            image = Image.open(buf)
            
            # Save to new buffer in JPEG format (smaller file size)
            jpeg_buf = io.BytesIO()
            image.save(jpeg_buf, format='JPEG', quality=85)
            jpeg_buf.seek(0)
            
            # Send the image
            asyncio.create_task(
                update.message.reply_photo(
                    photo=jpeg_buf,
                    caption=f"{result.symbol} {result.interval} chart with FLDs"
                )
            )
            
        except Exception as e:
            logger.error(f"Error sending chart image: {e}")
            asyncio.create_task(
                update.message.reply_text("Could not generate chart visualization")
            )
    
    async def _market_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE'):
        """Handle /market command for overall market analysis"""
        if not self.scanner:
            await update.message.reply_text("Scanner not available")
            return
        
        # Send initial response
        message = await update.message.reply_text("Analyzing overall market conditions...")
        
        try:
            # Analyze market index (e.g., NIFTY for Indian market)
            from concurrent.futures import ThreadPoolExecutor
            
            def run_analysis():
                # Analyze market index
                index_symbol = "NIFTY"
                params = ScanParameters(lookback=5000)
                result = self.scanner.analyze_symbol(index_symbol, "daily", params)
                
                # Get market breadth by scanning top stocks
                top_stocks = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]  # Example top stocks
                stock_results = []
                
                for symbol in top_stocks:
                    try:
                        stock_result = self.scanner.analyze_symbol(symbol, "daily", params)
                        if stock_result:
                            stock_results.append(stock_result)
                    except:
                        pass
                
                return {
                    "index_result": result,
                    "stock_results": stock_results
                }
            
            # Run in thread pool
            with ThreadPoolExecutor() as executor:
                future = executor.submit(run_analysis)
                result = future.result()
            
            index_result = result["index_result"]
            stock_results = result["stock_results"]
            
            if not index_result:
                await message.edit_text("Could not analyze market index")
                return
            
            # Calculate market breadth
            bullish_stocks = sum(1 for r in stock_results if "Buy" in r.signal)
            bearish_stocks = sum(1 for r in stock_results if "Sell" in r.signal)
            neutral_stocks = len(stock_results) - bullish_stocks - bearish_stocks
            
            # Format the market analysis
            response = f"*Market Analysis - {index_result.symbol}*\n\n"
            
            # Index signal
            signal_icon = "📈" if "Buy" in index_result.signal else "📉" if "Sell" in index_result.signal else "⚖️"
            response += f"*Market Signal:* {signal_icon} {index_result.signal} ({index_result.confidence})\n"
            response += f"*Signal Strength:* {index_result.combined_strength:.2f}\n\n"
            
            # Cycle information
            response += f"*Market Cycles:* {', '.join(str(c) for c in index_result.cycles)}\n\n"
            
            # Market breadth
            response += "*Market Breadth:*\n"
            response += f"📈 Bullish Stocks: {bullish_stocks}/{len(stock_results)}\n"
            response += f"📉 Bearish Stocks: {bearish_stocks}/{len(stock_results)}\n"
            response += f"⚖️ Neutral Stocks: {neutral_stocks}/{len(stock_results)}\n\n"
            
            # Market outlook
            response += "*Market Outlook:*\n"
            if "Buy" in index_result.signal and bullish_stocks > bearish_stocks:
                response += "✅ Bullish bias - look for buying opportunities in strong stocks"
            elif "Sell" in index_result.signal and bearish_stocks > bullish_stocks:
                response += "❌ Bearish bias - reduce long exposure and consider short positions"
            else:
                response += "⚠️ Mixed signals - selective trading and reduced position sizes advised"
            
            # Send the analysis
            await message.edit_text(response, parse_mode="Markdown")
            
            # Send chart for the index
            self._send_chart_image(index_result, update)
            
        except Exception as e:
            logger.error(f"Error in market command: {e}")
            await message.edit_text(f"Error analyzing market: {str(e)}")
    
    async def _report_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE'):
        """Handle /report command to get summary of last scan"""
        # Get arguments (optional interval)
        args = context.args
        interval = args[0].lower() if args else "daily"
        
        # Validate interval
        valid_intervals = ["weekly", "daily", "4h", "1h", "15min", "5min"]
        if interval not in valid_intervals:
            await update.message.reply_text(
                f"Invalid interval. Please use one of: {', '.join(valid_intervals)}"
            )
            return
        
        # Send initial response
        message = await update.message.reply_text(f"Generating {interval} scan report...")
        
        try:
            # In a real implementation, this would access the stored scan results
            # For now, we'll generate a placeholder report
            report = f"*📊 FIBONACCI CYCLE SCAN REPORT ({interval.upper()})*\n\n"
            report += "This is a placeholder report. In the full implementation, this would show:\n\n"
            report += "📈 *Top Buy Signals*\n"
            report += "1. SYMBOL1 - Strong Buy (2.45)\n"
            report += "2. SYMBOL2 - Buy (1.87)\n"
            report += "3. SYMBOL3 - Buy (1.52)\n\n"
            report += "📉 *Top Sell Signals*\n"
            report += "1. SYMBOL4 - Strong Sell (-2.33)\n"
            report += "2. SYMBOL5 - Sell (-1.91)\n"
            report += "3. SYMBOL6 - Sell (-1.63)\n\n"
            report += "🔄 *Recent Crossings*\n"
            report += "- SYMBOL7: Bullish 34-cycle (2 bars ago)\n"
            report += "- SYMBOL8: Bearish 21-cycle (1 bar ago)\n\n"
            report += f"Report generated at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            await message.edit_text(report, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in report command: {e}")
            await message.edit_text(f"Error generating report: {str(e)}")
    
    async def _backtest_command(self, update: 'Update', context: 'ContextTypes.DEFAULT_TYPE'):
        """Handle /backtest command to run a quick backtest"""
        if not self.scanner:
            await update.message.reply_text("Scanner not available")
            return
        
        # Get arguments
        args = context.args
        if len(args) < 1:
            await update.message.reply_text("Please provide a symbol. Example: /backtest RELIANCE 90")
            return
        
        symbol = args[0].upper()
        days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 90
        
        # Send initial response
        message = await update.message.reply_text(f"Running {days}-day backtest for {symbol}...")
        
        try:
            # Fetch data and run backtest
            from concurrent.futures import ThreadPoolExecutor
            
            def run_backtest():
                # Fetch data
                params = ScanParameters(lookback=max(5000, days * 2))
                data = self.scanner.fetch_data(symbol, "daily", lookback=params.lookback)
                
                if data is None or len(data) < days:
                    return None
                
                # Use only the specified number of days
                data = data.iloc[-days:]
                
                # Run backtest
                backtest = BacktestEngine(data, params)
                results = backtest.run_backtest(
                    strategy_type="fld_crossover",
                    stop_loss_type="atr",
                    take_profit_type="next_cycle",
                    position_sizing="risk_based"
                )
                
                # Generate equity curve chart
                fig = backtest.plot_equity_curve()
                
                return {
                    "results": results,
                    "fig": fig
                }
            
            # Run in thread pool
            with ThreadPoolExecutor() as executor:
                future = executor.submit(run_backtest)
                result = future.result()
            
            if result is None:
                await message.edit_text(f"Insufficient data for {symbol} backtest")
                return
            
            backtest_results = result["results"]
            metrics = backtest_results["metrics"]
            
            # Format the backtest results
            response = f"*Backtest Results: {symbol} ({days} days)*\n\n"
            
            # Key metrics
            response += "*Performance Metrics:*\n"
            response += f"- Total Return: {metrics['total_return']:.2%}\n"
            response += f"- Win Rate: {metrics['win_rate']:.2%}\n"
            response += f"- Profit Factor: {metrics['profit_factor']:.2f}\n"
            response += f"- Max Drawdown: {metrics['max_drawdown']:.2%}\n"
            response += f"- Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n"
            response += f"- Total Trades: {metrics['total_trades']}\n\n"
            
            # Interpretation
            response += "*Interpretation:*\n"
            if metrics['total_return'] > 0 and metrics['sharpe_ratio'] > 1:
                response += "✅ Strategy shows positive results on this instrument"
            elif metrics['total_return'] > 0:
                response += "⚠️ Strategy is profitable but with significant drawdowns"
            else:
                response += "❌ Strategy does not perform well on this instrument"
            
            # Send the results
            await message.edit_text(response, parse_mode="Markdown")
            
            # Send equity curve chart
            try:
                import io
                fig = result["fig"]
                
                # Save to buffer
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=100)
                plt.close(fig)  # Close to free memory
                
                # Send the image
                buf.seek(0)
                asyncio.create_task(
                    update.message.reply_photo(
                        photo=buf,
                        caption=f"{symbol} {days}-day Backtest Equity Curve"
                    )
                )
                
            except Exception as chart_error:
                logger.error(f"Error sending backtest chart: {chart_error}")
            
        except Exception as e:
            logger.error(f"Error in backtest command: {e}")
            await message.edit_text(f"Error running backtest for {symbol}: {str(e)}")
    
    def send_scan_report(self, timeframe, buy_signals, sell_signals, recent_crossings):
        """
        Send a formatted scan report
        
        Args:
            timeframe: Timeframe of the scan
            buy_signals: List of buy