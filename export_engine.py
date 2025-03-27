import pandas as pd
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ExportEngine:
    """Export engine for scan results"""
    
    def export_to_csv(self, results, filename=None):
        """
        Export scan results to CSV
        
        Args:
            results: List of ScanResult objects
            filename: Output filename or None to auto-generate
            
        Returns:
            Path to exported file
        """
        try:
            if not results:
                logger.warning("No results to export")
                return None
            
            # Create dataframe
            data = []
            for result in results:
                # Ensure we have all required properties
                if not hasattr(result, 'symbol') or not hasattr(result, 'signal'):
                    continue
                
                data.append({
                    'symbol': result.symbol,
                    'interval': result.interval if hasattr(result, 'interval') else 'unknown',
                    'last_price': result.last_price if hasattr(result, 'last_price') else 0,
                    'last_date': result.last_date if hasattr(result, 'last_date') else '',
                    'signal': result.signal,
                    'confidence': result.confidence if hasattr(result, 'confidence') else 'Low',
                    'strength': result.combined_strength if hasattr(result, 'combined_strength') else 0,
                    'cycles': ', '.join(str(c) for c in result.cycles) if hasattr(result, 'cycles') else '',
                    'has_key_cycles': result.has_key_cycles if hasattr(result, 'has_key_cycles') else False
                })
            
            if not data:
                logger.warning("No valid results to export")
                return None
                
            df = pd.DataFrame(data)
            
            # Generate filename if not provided
            if filename is None:
                # Create reports directory if it doesn't exist
                os.makedirs('./data/reports', exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                interval = results[0].interval if hasattr(results[0], 'interval') else 'unknown'
                filename = f"./data/reports/fibonacci_scan_{interval}_{timestamp}.csv"
            
            # Export to CSV
            df.to_csv(filename, index=False)
            logger.info(f"Exported {len(results)} results to {filename}")
            
            # Also save to Google Drive if available
            try:
                from integration.google_drive_integration import drive_storage
                
                if os.path.exists(drive_storage.base_path):
                    drive_file = drive_storage.save_file(filename, "reports")
                    logger.info(f"Saved CSV to Google Drive: {drive_file}")
            except Exception as e:
                logger.error(f"Error saving to Google Drive: {e}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return None
    
    def export_to_excel(self, results, filename=None):
        """
        Export scan results to Excel
        
        Args:
            results: List of ScanResult objects
            filename: Output filename or None to auto-generate
            
        Returns:
            Path to exported file
        """
        try:
            if not results:
                logger.warning("No results to export")
                return None
            
            # Create dataframe
            data = []
            for result in results:
                # Ensure we have all required properties
                if not hasattr(result, 'symbol') or not hasattr(result, 'signal'):
                    continue
                    
                data.append({
                    'symbol': result.symbol,
                    'interval': result.interval if hasattr(result, 'interval') else 'unknown',
                    'last_price': result.last_price if hasattr(result, 'last_price') else 0,
                    'last_date': result.last_date if hasattr(result, 'last_date') else '',
                    'signal': result.signal,
                    'confidence': result.confidence if hasattr(result, 'confidence') else 'Low',
                    'strength': result.combined_strength if hasattr(result, 'combined_strength') else 0,
                    'cycles': ', '.join(str(c) for c in result.cycles) if hasattr(result, 'cycles') else '',
                    'has_key_cycles': 'Yes' if (hasattr(result, 'has_key_cycles') and result.has_key_cycles) else 'No',
                    'entry_strategy': result.guidance['entry_strategy'] if (hasattr(result, 'guidance') and 'entry_strategy' in result.guidance) else '',
                    'exit_strategy': result.guidance['exit_strategy'] if (hasattr(result, 'guidance') and 'exit_strategy' in result.guidance) else '',
                })
            
            if not data:
                logger.warning("No valid results to export")
                return None
                
            df = pd.DataFrame(data)
            
            # Generate filename if not provided
            if filename is None:
                # Create reports directory if it doesn't exist
                os.makedirs('./data/reports', exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                interval = results[0].interval if hasattr(results[0], 'interval') else 'unknown'
                filename = f"./data/reports/fibonacci_scan_{interval}_{timestamp}.xlsx"
            
            # Export to Excel with formatting
            writer = pd.ExcelWriter(filename, engine='xlsxwriter')
            df.to_excel(writer, sheet_name='Scan Results', index=False)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Scan Results']
            
            # Define formats
            header_format = workbook.add_format({
                'bold': True, 
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Add conditional formatting
            # Buy signals in green
            worksheet.conditional_format(1, df.columns.get_loc('signal'), len(df), df.columns.get_loc('signal'), {
                'type': 'text',
                'criteria': 'containing',
                'value': 'Buy',
                'format': workbook.add_format({'bg_color': '#C6EFCE'})
            })
            
            # Sell signals in red
            worksheet.conditional_format(1, df.columns.get_loc('signal'), len(df), df.columns.get_loc('signal'), {
                'type': 'text',
                'criteria': 'containing',
                'value': 'Sell',
                'format': workbook.add_format({'bg_color': '#FFC7CE'})
            })
            
            # Apply header format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Auto-adjust column widths
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)
            
            # Close the writer
            writer.close()
            
            logger.info(f"Exported {len(results)} results to {filename}")
            
            # Also save to Google Drive if available
            try:
                from integration.google_drive_integration import drive_storage
                
                if os.path.exists(drive_storage.base_path):
                    drive_file = drive_storage.save_file(filename, "reports")
                    logger.info(f"Saved Excel file to Google Drive: {drive_file}")
            except Exception as e:
                logger.error(f"Error saving to Google Drive: {e}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return None
    
    def generate_html_report(self, results, filename=None):
        """
        Generate HTML report from scan results
        
        Args:
            results: List of ScanResult objects
            filename: Output filename or None to auto-generate
            
        Returns:
            Path to exported file
        """
        try:
            if not results:
                logger.warning("No results to export")
                return None
            
            # Generate filename if not provided
            if filename is None:
                # Create reports directory if it doesn't exist
                os.makedirs('./data/reports', exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                interval = results[0].interval if hasattr(results[0], 'interval') else 'unknown'
                filename = f"./data/reports/fibonacci_report_{interval}_{timestamp}.html"
            
            # Create HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Fibonacci Cycle Scanner Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1, h2, h3 {{ color: #007bff; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f8f9fa; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .buy {{ background-color: #d4edda; }}
                    .sell {{ background-color: #f8d7da; }}
                    .header {{ background-color: #6c757d; color: white; padding: 10px; }}
                    .footer {{ margin-top: 30px; font-size: 0.8em; color: #6c757d; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Fibonacci Cycle Scanner Report</h1>
                    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <h2>Summary</h2>
                <p>Total symbols analyzed: {len(results)}</p>
                <p>Interval: {results[0].interval if hasattr(results[0], 'interval') else 'unknown'}</p>
                
                <h2>Buy Signals</h2>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Last Price</th>
                        <th>Signal</th>
                        <th>Strength</th>
                        <th>Confidence</th>
                        <th>Cycles</th>
                        <th>Entry Strategy</th>
                    </tr>
            """
            
            # Add buy signals
            buy_signals = [r for r in results if hasattr(r, 'signal') and "Buy" in r.signal]
            buy_signals.sort(key=lambda x: getattr(x, 'combined_strength', 0), reverse=True)
            
            for result in buy_signals:
                html_content += f"""
                    <tr class="buy">
                        <td>{result.symbol}</td>
                        <td>{result.last_price if hasattr(result, 'last_price') else 'N/A'}</td>
                        <td>{result.signal}</td>
                        <td>{result.combined_strength:.2f if hasattr(result, 'combined_strength') else 'N/A'}</td>
                        <td>{result.confidence if hasattr(result, 'confidence') else 'N/A'}</td>
                        <td>{', '.join(str(c) for c in result.cycles) if hasattr(result, 'cycles') else 'N/A'}</td>
                        <td>{result.guidance['entry_strategy'] if (hasattr(result, 'guidance') and 'entry_strategy' in result.guidance) else 'N/A'}</td>
                    </tr>
                """
            
            html_content += """
                </table>
                
                <h2>Sell Signals</h2>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Last Price</th>
                        <th>Signal</th>
                        <th>Strength</th>
                        <th>Confidence</th>
                        <th>Cycles</th>
                        <th>Entry Strategy</th>
                    </tr>
            """
            
            # Add sell signals
            sell_signals = [r for r in results if hasattr(r, 'signal') and "Sell" in r.signal]
            sell_signals.sort(key=lambda x: abs(getattr(x, 'combined_strength', 0)), reverse=True)
            
            for result in sell_signals:
                html_content += f"""
                    <tr class="sell">
                        <td>{result.symbol}</td>
                        <td>{result.last_price if hasattr(result, 'last_price') else 'N/A'}</td>
                        <td>{result.signal}</td>
                        <td>{result.combined_strength:.2f if hasattr(result, 'combined_strength') else 'N/A'}</td>
                        <td>{result.confidence if hasattr(result, 'confidence') else 'N/A'}</td>
                        <td>{', '.join(str(c) for c in result.cycles) if hasattr(result, 'cycles') else 'N/A'}</td>
                        <td>{result.guidance['entry_strategy'] if (hasattr(result, 'guidance') and 'entry_strategy' in result.guidance) else 'N/A'}</td>
                    </tr>
                """
            
            html_content += """
                </table>
                
                <div class="footer">
                    <p>Fibonacci Cycle Scanner - Based on the discovery of universal Fibonacci market cycles</p>
                    <p>This system detects cycles that follow the Golden Ratio relationship (21:34 ≈ 1.618)</p>
                </div>
            </body>
            </html>
            """
            
            # Write HTML to file
            with open(filename, 'w') as f:
                f.write(html_content)
            
            logger.info(f"Generated HTML report with {len(results)} results to {filename}")
            
            # Also save to Google Drive if available
            try:
                from integration.google_drive_integration import drive_storage
                
                if os.path.exists(drive_storage.base_path):
                    drive_file = drive_storage.save_file(filename, "reports")
                    logger.info(f"Saved HTML report to Google Drive: {drive_file}")
            except Exception as e:
                logger.error(f"Error saving to Google Drive: {e}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
            return None