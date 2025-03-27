"""
Performance monitoring utilities for Fibonacci Cycle Trading System
"""
import time
import logging
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """
    Monitor and track performance metrics for various operations
    """
    
    def __init__(self, log_file="./logs/performance.log"):
        """
        Initialize performance monitor
        
        Args:
            log_file: Path to performance log file
        """
        self.log_file = log_file
        self.timers = {}
        self.metrics = {
            "cycle_detection": {
                "calls": 0,
                "total_time": 0,
                "max_time": 0,
                "avg_time": 0
            },
            "data_fetch": {
                "calls": 0,
                "total_time": 0,
                "max_time": 0,
                "avg_time": 0,
                "cache_hits": 0,
                "cache_misses": 0
            },
            "batch_scan": {
                "calls": 0,
                "total_time": 0,
                "max_time": 0,
                "avg_time": 0,
                "total_symbols": 0
            },
            "signal_generation": {
                "calls": 0,
                "total_time": 0,
                "max_time": 0,
                "avg_time": 0
            },
            "backtest": {
                "calls": 0,
                "total_time": 0,
                "max_time": 0,
                "avg_time": 0,
                "total_trades": 0
            },
            "web_render": {
                "calls": 0,
                "total_time": 0,
                "max_time": 0,
                "avg_time": 0
            }
        }
        
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except Exception as e:
                logger.error(f"Failed to create log directory: {e}")
    
    def start_timer(self, operation, metadata=None):
        """
        Start timing an operation
        
        Args:
            operation: Name of the operation
            metadata: Additional information about the operation
        """
        self.timers[operation] = {
            "start_time": time.time(),
            "metadata": metadata or {}
        }
    
    def stop_timer(self, operation, success=True, result_metadata=None):
        """
        Stop timing an operation and record metrics
        
        Args:
            operation: Name of the operation
            success: Whether the operation was successful
            result_metadata: Additional metadata about the result
            
        Returns:
            Elapsed time in seconds
        """
        if operation not in self.timers:
            logger.warning(f"No timer found for operation: {operation}")
            return 0
        
        # Calculate elapsed time
        elapsed_time = time.time() - self.timers[operation]["start_time"]
        
        # Get metadata
        metadata = self.timers[operation]["metadata"]
        metadata.update(result_metadata or {})
        
        # Update metrics if the operation is known
        if operation in self.metrics:
            self.metrics[operation]["calls"] += 1
            self.metrics[operation]["total_time"] += elapsed_time
            self.metrics[operation]["max_time"] = max(self.metrics[operation]["max_time"], elapsed_time)
            self.metrics[operation]["avg_time"] = self.metrics[operation]["total_time"] / self.metrics[operation]["calls"]
            
            # Update operation-specific metrics
            if operation == "data_fetch":
                if metadata.get("cache_hit", False):
                    self.metrics[operation]["cache_hits"] += 1
                else:
                    self.metrics[operation]["cache_misses"] += 1
            
            elif operation == "batch_scan":
                self.metrics[operation]["total_symbols"] += metadata.get("symbols_processed", 0)
            
            elif operation == "backtest":
                self.metrics[operation]["total_trades"] += metadata.get("total_trades", 0)
        
        # Log the performance data
        self._log_performance(operation, elapsed_time, success, metadata)
        
        # Clean up timer
        del self.timers[operation]
        
        return elapsed_time
    
    def _log_performance(self, operation, elapsed_time, success, metadata):
        """
        Log performance data to file
        
        Args:
            operation: Name of the operation
            elapsed_time: Elapsed time in seconds
            success: Whether the operation was successful
            metadata: Operation metadata
        """
        try:
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Format metadata
            metadata_str = ", ".join(f"{k}={v}" for k, v in metadata.items())
            
            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "elapsed_time": elapsed_time,
                "success": success,
                "metadata": metadata
            }
            
            # Write to log file
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        
        except Exception as e:
            logger.error(f"Error logging performance data: {e}")
    
    def get_metrics(self):
        """
        Get current performance metrics
        
        Returns:
            Dictionary with performance metrics
        """
        return self.metrics
    
    def reset_metrics(self):
        """Reset all performance metrics"""
        for operation in self.metrics:
            self.metrics[operation] = {
                "calls": 0,
                "total_time": 0,
                "max_time": 0,
                "avg_time": 0
            }
            
            # Restore operation-specific fields
            if operation == "data_fetch":
                self.metrics[operation].update({
                    "cache_hits": 0,
                    "cache_misses": 0
                })
            
            elif operation == "batch_scan":
                self.metrics[operation].update({
                    "total_symbols": 0
                })
            
            elif operation == "backtest":
                self.metrics[operation].update({
                    "total_trades": 0
                })
    
    def generate_report(self):
        """
        Generate a performance report
        
        Returns:
            Dictionary with report data
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics,
            "summary": {}
        }
        
        # Add summary metrics
        total_calls = sum(m["calls"] for m in self.metrics.values())
        total_time = sum(m["total_time"] for m in self.metrics.values())
        
        report["summary"] = {
            "total_calls": total_calls,
            "total_time": total_time,
            "operations_distribution": {
                op: (m["calls"] / total_calls if total_calls > 0 else 0)
                for op, m in self.metrics.items()
            },
            "time_distribution": {
                op: (m["total_time"] / total_time if total_time > 0 else 0)
                for op, m in self.metrics.items()
            }
        }
        
        # Add cache efficiency
        data_fetch = self.metrics["data_fetch"]
        total_fetches = data_fetch["cache_hits"] + data_fetch["cache_misses"]
        
        report["summary"]["cache_hit_ratio"] = (
            data_fetch["cache_hits"] / total_fetches if total_fetches > 0 else 0
        )
        
        # Add recommendations
        report["recommendations"] = self._generate_recommendations()
        
        return report
    
    def _generate_recommendations(self):
        """
        Generate performance recommendations
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Check data fetch cache efficiency
        data_fetch = self.metrics["data_fetch"]
        total_fetches = data_fetch["cache_hits"] + data_fetch["cache_misses"]
        cache_hit_ratio = data_fetch["cache_hits"] / total_fetches if total_fetches > 0 else 0
        
        if cache_hit_ratio < 0.5 and total_fetches > 10:
            recommendations.append(
                "Low cache hit ratio (below 50%). Consider increasing cache expiry time."
            )
        
        # Check batch scan performance
        batch_scan = self.metrics["batch_scan"]
        if batch_scan["calls"] > 0:
            avg_time_per_symbol = batch_scan["total_time"] / batch_scan["total_symbols"] if batch_scan["total_symbols"] > 0 else 0
            
            if avg_time_per_symbol > 1.0:
                recommendations.append(
                    f"Slow symbol processing (avg {avg_time_per_symbol:.2f}s per symbol). Consider enabling GPU acceleration."
                )
        
        # Check cycle detection performance
        cycle_detection = self.metrics["cycle_detection"]
        if cycle_detection["calls"] > 0 and cycle_detection["avg_time"] > 0.5:
            recommendations.append(
                f"Slow cycle detection (avg {cycle_detection['avg_time']:.2f}s). Consider using a smaller lookback period or enabling GPU."
            )
        
        return recommendations
    
    def log_memory_usage(self):
        """Log current memory usage to performance log"""
        try:
            import psutil
            
            # Get process memory info
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            # Log as a custom operation
            self._log_performance(
                "memory_snapshot",
                0,
                True,
                {
                    "rss_mb": memory_info.rss / (1024 * 1024),
                    "vms_mb": memory_info.vms / (1024 * 1024),
                    "percent": process.memory_percent()
                }
            )
            
            return {
                "rss_mb": memory_info.rss / (1024 * 1024),
                "vms_mb": memory_info.vms / (1024 * 1024),
                "percent": process.memory_percent()
            }
        
        except ImportError:
            logger.warning("psutil not installed, cannot log memory usage")
            return None
        
        except Exception as e:
            logger.error(f"Error logging memory usage: {e}")
            return None

# Create global instance
performance_monitor = PerformanceMonitor()