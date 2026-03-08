import asyncio
from typing import Any

# Global registry for active task event queues
# Managed by main.py but accessible by nodes via governor
task_events: dict[str, asyncio.Queue[dict[str, Any]]] = {}
