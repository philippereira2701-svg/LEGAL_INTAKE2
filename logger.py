import os
import logging
from datetime import datetime

class LexLogger:
    """
    Centralized high-fidelity logging for LEGAL_PRJ Architecture.
    """
    def __init__(self, log_file="legal_prj_core.log"):
        self.logger = logging.getLogger("LEGAL_PRJ")
        self.logger.setLevel(logging.INFO)
        
        # Create handlers
        f_handler = logging.FileHandler(log_file)
        c_handler = logging.StreamHandler()
        
        # Create formatters and add it to handlers
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        c_format = logging.Formatter('%(name)s [%(levelname)s] - %(message)s')
        f_handler.setFormatter(f_format)
        c_handler.setFormatter(c_format)
        
        # Add handlers to the logger
        if not self.logger.handlers:
            self.logger.addHandler(f_handler)
            self.logger.addHandler(c_handler)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg, exc_info=True):
        self.logger.error(msg, exc_info=exc_info)

    def warning(self, msg):
        self.logger.warning(msg)

    def audit_lead(self, lead_id, action, status="success"):
        """Specific audit trail for lead lifecycle."""
        self.info(f"AUDIT | Lead:{lead_id} | Action:{action} | Status:{status}")

# Global instance
logger = LexLogger()
