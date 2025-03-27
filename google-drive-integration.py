"""
Google Drive integration for Fibonacci Cycle Trading System
"""
import os
import logging
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

class DriveStorage:
    """
    Class to handle storage on Google Drive
    """
    
    def __init__(self, base_path="G:\\My Drive\\FLD-FIB-CYCLE"):
        """
        Initialize the drive storage
        
        Args:
            base_path: Base path on Google Drive
        """
        self.base_path = base_path
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        try:
            # Create main directory if it doesn't exist
            if not os.path.exists(self.base_path):
                os.makedirs(self.base_path)
                logger.info(f"Created base directory: {self.base_path}")
            
            # Create subdirectories
            subdirs = [
                "reports",
                "logs",
                "data",
                "data/cache",
                "data/symbols",
                "charts"
            ]
            
            for subdir in subdirs:
                dir_path = os.path.join(self.base_path, subdir)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                    logger.info(f"Created directory: {dir_path}")
                    
        except Exception as e:
            logger.error(f"Error creating directories on Google Drive: {e}")
            
    def get_path(self, path_type):
        """
        Get path for a specific type
        
        Args:
            path_type: Type of path ("reports", "logs", "data", "charts", etc.)
            
        Returns:
            Full path
        """
        path_map = {
            "reports": os.path.join(self.base_path, "reports"),
            "logs": os.path.join(self.base_path, "logs"),
            "data": os.path.join(self.base_path, "data"),
            "cache": os.path.join(self.base_path, "data", "cache"),
            "symbols": os.path.join(self.base_path, "data", "symbols"),
            "charts": os.path.join(self.base_path, "charts")
        }
        
        if path_type in path_map:
            return path_map[path_type]
        else:
            return self.base_path
    
    def save_file(self, file_path, destination_type):
        """
        Save a file to Google Drive
        
        Args:
            file_path: Path to source file
            destination_type: Type of destination ("reports", "logs", "data", "charts")
            
        Returns:
            Path to saved file on Google Drive
        """
        try:
            # Get destination directory
            dest_dir = self.get_path(destination_type)
            
            # Get filename
            filename = os.path.basename(file_path)
            
            # Create destination path
            dest_path = os.path.join(dest_dir, filename)
            
            # Copy file
            shutil.copy2(file_path, dest_path)
            
            logger.info(f"Saved file to Google Drive: {dest_path}")
            return dest_path
            
        except Exception as e:
            logger.error(f"Error saving file to Google Drive: {e}")
            return None
    
    def get_symbols_file_path(self, filename="default_symbols.csv"):
        """
        Get path to symbols file
        
        Args:
            filename: Filename of symbols file
            
        Returns:
            Full path to symbols file
        """
        return os.path.join(self.get_path("symbols"), filename)
    
    def list_files(self, path_type, file_extension=None):
        """
        List files in a specific path
        
        Args:
            path_type: Type of path ("reports", "logs", "data", "charts")
            file_extension: Filter by file extension (e.g., ".csv")
            
        Returns:
            List of filenames
        """
        try:
            dir_path = self.get_path(path_type)
            
            if not os.path.exists(dir_path):
                return []
            
            files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
            
            if file_extension:
                files = [f for f in files if f.endswith(file_extension)]
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files in {path_type}: {e}")
            return []
    
    def create_dated_subdirectory(self, path_type):
        """
        Create a dated subdirectory
        
        Args:
            path_type: Type of path ("reports", "logs", "data", "charts")
            
        Returns:
            Path to created directory
        """
        try:
            # Get parent directory
            parent_dir = self.get_path(path_type)
            
            # Create dated directory name
            date_str = datetime.now().strftime("%Y%m%d")
            dir_name = f"{path_type}_{date_str}"
            
            # Create directory path
            dir_path = os.path.join(parent_dir, dir_name)
            
            # Create directory if it doesn't exist
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                logger.info(f"Created dated directory: {dir_path}")
            
            return dir_path
            
        except Exception as e:
            logger.error(f"Error creating dated subdirectory: {e}")
            return self.get_path(path_type)  # Fall back to parent directory

# Create global instance
drive_storage = DriveStorage()