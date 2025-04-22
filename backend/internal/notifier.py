"""
Module for Notifier
"""

from dataclasses import dataclass
import math
from typing import Optional

from internal.temp_storage import TempStorage


@dataclass
class Notifier:
    """
    Class to notify about progress.
    """
    task_id: Optional[str]
    temp_store: Optional[TempStorage]

    def notify(self, progress: int|float, status: str = "processing"):
        """
        Notify progress change
        """
        if self.temp_store is None or self.task_id is None:
            return
        self.temp_store.cache_progress(self.task_id, progress, status)

    def loop_notify(self, iteration: int, lower: int, 
                    upper: int, max_iter:int, 
                    status: str = "processing"):
        """
        Notify progress in the loop
        """
        progress = lower + math.floor(iteration * (upper - lower) / max_iter)
        self.notify(progress, status)
