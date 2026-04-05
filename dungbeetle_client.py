import requests
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("DUNGBEETLE")

class DungBeetleClient:
    """
    Python client for DungBeetle (github.com/zerodha/dungbeetle).
    Offloads heavy SQL read jobs to an async reporting layer.
    """
    
    def __init__(self):
        self.base_url = os.getenv("DUNGBEETLE_URL", "http://localhost:8080")
        self.api_key = os.getenv("DUNGBEETLE_API_KEY")

    def submit_job(self, query: str, db_name: str = "primary") -> Optional[str]:
        """Submit a SQL query to be executed asynchronously"""
        try:
            resp = requests.post(
                f"{self.base_url}/jobs",
                json={"query": query, "db": db_name},
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            if resp.status_code == 200:
                return resp.json().get("job_id")
            logger.error(f"DungBeetle submission failed: {resp.text}")
        except Exception as e:
            logger.error(f"DungBeetle connection error: {e}")
        return None

    def get_result(self, job_id: str) -> Dict[str, Any]:
        """Poll or fetch the result of a submitted job"""
        try:
            resp = requests.get(f"{self.base_url}/jobs/{job_id}")
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"DungBeetle result fetch error: {e}")
        return {"status": "error"}

    def execute_instant(self, query: str) -> Optional[List[Dict]]:
        """Synchronous fetch for optimized/cached reporting queries"""
        try:
            resp = requests.post(
                f"{self.base_url}/query",
                json={"query": query},
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except Exception as e:
            logger.error(f"DungBeetle instant query failed: {e}")
        return None
