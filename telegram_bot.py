from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio
import threading
import time
from datetime import datetime
import pandas as pd
import io
import logging
import os

logger = logging.getLogger(__name__)

class TelegramReporter:
    """Telegram bot for sending scan reports and notifications"""
    
    def __init__(self, token=None, chat_id=None, scanner=None):
        """
        Initialize Telegram reporter
        
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
        self.loop = None
        self.running = False
        self.initialized = False
        
        # Only attempt initialization if token is provided
        if token and token != 'YOUR_TELEGRAM_BOT_TOKEN' and chat_id and chat_id != 'YOUR_TELEGRAM_CHAT_ID':
            try:
                # Import here to avoid dependency for those who don't use Telegram
                from telegram import Bot
                from telegram.ext import Application
                
                # Initialize the bot
                self.bot = Bot(token)
                
                # Create application
                self.application = Application.builder().token(token).build()
                
                # Add handlers
                self._add_handlers()
                
                # Start the bot in a separate thread
                self.bot_thread = threading.Thread(target=self.start_bot)
                self.bot_thread.daemon = True
                self.bot_thread.start()
                
                self.initialized = True
                logger.info("Telegram bot initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                self.initialized = False
        else:
            logger.warning("Telegram bot not initialized: Missing or invalid token/chat_id")
            self.initialized = False
    
    def _add_handlers(self):
        """Add command handlers to the bot"""
        from telegram.ext import CommandHandler
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("scan", self.scan_command))
        self.application.add_handler(CommandHandler("report", self.report_command))
        self.application.add_handler(CommandHandler("analysis", self.analysis_command))
    
    def start_bot(self):
        """Start the bot polling in background using asyncio"""
        if not self.initialized:
            return
            
        try:
            # Create a new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Start polling
            self.running = True
            self.loop.run_until_complete(self.application.run_polling(allowed_updates=Update.ALL_TYPES))
            
        except Exception as e:
            logger.error(f"Error starting bot polling: {e}")
        finally:
            if self.loop and self.loop.is_running():
                self.loop.close()
    
    def stop_bot(self):
        """Stop the bot polling"""
        if self.running and self.application and self.loop:
            try:
                # This approach is a bit hacky but works to stop the bot
                asyncio.run_coroutine_threadsafe(self.application.stop(), self.loop)
                self.running = False
                logger.info("Telegram bot polling stopped")
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
    
    async def send_message_async(self, message):
        """Send a message asynchronously"""
        if not self.initialized:
            logger.warning("Telegram bot not initialized")
            return False
            
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode="Markdown")
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_message(self, message):
        """Send a message through Telegram (sync wrapper)"""
        if not self.initialized:
            logger.warning("Telegram bot not initialized or properly configured")
            return False
            
        try:
            # For synchronous code, we need to create a new event loop
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(self.send_message_async(message))
            loop.close()
            logger.info(f"Telegram message sent: {message[:50]}...")
            return result
        except Exception as e:
            logger.error(f"Error in send_message: {e}")
            return False
    
    async def send_image_async(self, plot_buffer, caption=""):
        """Send an image asynchronously"""
        if not self.initialized:
            logger.warning("Telegram bot not initialized")
            return False
            
        try:
            plot_buffer.seek(0)
            await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=plot_buffer,
                caption=caption
            )
            return True
        except Exception as e:
            logger.error(f"Error sending image: {e}")
            return False
    
    def send_image(self, plot_buffer, caption=""):
        """Send an image (sync wrapper)"""
        if not self.initialized:
            logger.warning("Telegram bot not initialized or properly configured")
            return False
        
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(self.send_image_async(plot_buffer, caption))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Error in send_image: {e}")
            return False
    
    def send_scan_report(self, interval, total_symbols, symbols_with_cycles, buy_signals, sell_signals):
        """
        Send a formatted scan report
        
        Args:
            interval: Interval (e.g., "daily", "15min")
            total_symbols: Total number of symbols scanned
            symbols_with_cycles: Number of symbols with detected cycles
            buy_signals: Number of buy signals
            sell_signals: Number of sell signals
        """
        if not self.initialized:
            logger.warning("Telegram bot not initialized or properly configured - report not sent")
            return False
            
        report = f"🔍 *FIBONACCI SCAN REPORT* ({interval.upper()})\n\n"
        report += f"Total symbols scanned: {total_symbols}\n"
        report += f"Symbols with cycles: {symbols_with_cycles}\n"
        report += f"Buy signals: {buy_signals} 📈\n"
        report += f"Sell signals: {sell_signals} 📉\n"
        
        if buy_signals > 0:
            report += "\n🟢 *TOP BUY SIGNALS:* Coming soon"
            
        if sell_signals > 0:
            report += "\n🔴 *TOP SELL SIGNALS:* Coming soon"
            
        report += f"\n\nScan completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_message(report)
    
    # Command Handlers
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        await update.message.reply_text(
            f"Hello {user.first_name}! Welcome to the Fibonacci Cycle Scanner bot.\n\n"
            f"Use /help to see available commands."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "*Fibonacci Cycle Scanner Commands*\n\n"
            "*/scan SYMBOL [INTERVAL]* - Scan a single symbol\n"
            "Example: `/scan RELIANCE daily`\n\n"
            "*/analysis SYMBOL INTERVAL* - Detailed analysis of a symbol\n"
            "Example: `/analysis INFY daily`\n\n"
            "*/report [INTERVAL]* - Get latest scan report\n"
            "Example: `/report daily`\n\n"
            "Available intervals: daily, 4h, 1h, 15min, 5min"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /scan command"""
        if not self.scanner:
            await update.message.reply_text("Scanner not available. Please try again later.")
            return
        
        # Get arguments
        args = context.args
        if not args:
            await update.message.reply_text("Please provide a symbol to scan. Example: /scan RELIANCE")
            return
        
        symbol = args[0].upper()
        interval = args[1].lower() if len(args) > 1 else "daily"
        
        # Validate interval
        valid_intervals = ["daily", "4h", "1h", "15min", "5min"]
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
            
            # Try to send a chart image if available
            try:
                import io
                import matplotlib.pyplot as plt
                import numpy as np
                
                # Generate the chart
                chart_data = self.scanner.generate_plot_image(
                    result.symbol, 
                    result.plot_data, 
                    result.cycles, 
                    result.cycle_states,
                    as_base64=False
                )
                
                # Open the saved image
                with open(chart_data, 'rb') as f:
                    await update.message.reply_photo(
                        photo=f,
                        caption=f"{result.symbol} {result.interval} chart with FLDs"
                    )
                
            except Exception as chart_error:
                logger.error(f"Error sending chart image: {chart_error}")
                await update.message.reply_text("Could not generate chart visualization")
            
        except Exception as e:
            logger.error(f"Error in scan command: {e}")
            await message.edit_text(f"Error analyzing {symbol}: {str(e)}")
    
    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report command to get summary of last scan"""
        # Get arguments (optional interval)
        args = context.args
        interval = args[0].lower() if args else "daily"
        
        # Check if we have stored results
        await update.message.reply_text(
            f"The last {interval} scan results are not available yet.\n\n"
            f"Please run a scan first using the web interface or use /scan command."
        )
    
    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analysis command for detailed analysis"""
        # This is a more detailed version of the scan command
        await self.scan_command(update, context)