import logging
import os
import socket
from datetime import datetime, timezone

class RFC5424Formatter(logging.Formatter):
    """
    RFC 5424 Syslog Formatter
    Format: <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [SD-ELEMENT] MSG
    (VERSION is 1)
    """
    def __init__(self, facility=18, app_name=None):
        super().__init__()
        self.facility = facility
        self.app_name = app_name or os.environ.get("APP_NAME", "texcore-scanning")
        # Ensure max 48 chars, no spaces for app_name
        self.app_name = self.app_name.replace(" ", "-")[:48]
        self.hostname = socket.gethostname()[:255]
        self.procid = str(os.getpid())[:128]

    def _escape(self, value: str) -> str:
        """Escape backslash, double quote, and right bracket as per RFC 5424 §6.3.3"""
        return value.replace('\\', '\\\\').replace('"', '\\"').replace(']', '\\]')

    def _build_sd(self, params: dict) -> str:
        if not params:
            return "-"
        
        sd_elements = []
        for key, value in params.items():
            safe_key = str(key).replace(" ", "-").replace("=", "").replace('"', "")
            safe_value = self._escape(str(value))
            sd_elements.append(f'{safe_key}="{safe_value}"')
        
        if sd_elements:
            return f'[texcore@32473 {" ".join(sd_elements)}]'
        return "-"

    def format(self, record):
        # Severity mapping: EMERGENCY=0, ALERT=1, CRITICAL=2, ERROR=3, WARNING=4, NOTICE=5, INFO=6, DEBUG=7
        severity_map = {
            logging.CRITICAL: 2,
            logging.ERROR: 3,
            logging.WARNING: 4,
            logging.INFO: 6,
            logging.DEBUG: 7
        }
        severity = severity_map.get(record.levelno, 6) # Default INFO
        pri = (self.facility * 8) + severity
        
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec='milliseconds')
        
        msgid = str(record.name).replace(".", "-")[:32]
        
        sd_dict = getattr(record, 'sd', {})
        sd_element = self._build_sd(sd_dict)
        
        msg = record.getMessage()
        
        return f"<{pri}>1 {timestamp} {self.hostname} {self.app_name} {self.procid} {msgid} {sd_element} {msg}"
