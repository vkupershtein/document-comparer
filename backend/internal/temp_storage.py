"""
Module for temporary storage
"""
import os
from typing import Hashable, List, Dict, Any, Tuple  # pylint: disable=deprecated-class
import json

from redis import Redis


class TempStorage:
    """
    Class for temporary storage
    """

    def __init__(self, provider):
        self.provider = provider

    @classmethod
    def create_with_redis(cls, connection_string):
        """
        Create temporary storage with Redis
        """
        provider = Redis.from_url(connection_string,
                                  decode_responses=False)
        return cls(provider)

    def cache_progress(self, task_id: str,
                       progress: int|float,
                       status: str = "processing"):
        """
        Cache progress of the operation
        """
        self.provider.set(f"progress:{task_id}", progress, ex=10800)
        self.provider.set(f"status:{task_id}", status, ex=10800)

    def get_progress(self, task_id: str) -> Tuple[int | None, str | None]:
        """
        Get progress status
        """
        progress = self.provider.get(f"progress:{task_id}")
        status = self.provider.get(f"status:{task_id}")
        if progress is None or status is None:
            return None, None
        try:
            return int(progress), status
        except ValueError:
            return None, None

    def cache_result(self, task_id: str, dataset: List[Dict[Hashable, Any]]):
        """
        Cache result of the operation
        """
        rval = json.dumps(dataset)
        self.provider.set(f"result:{task_id}", rval, ex=10800)

    def get_result(self, task_id: str) -> List[Dict[Hashable, Any]] | None:
        """
        Get result of the operation
        """
        data = self.provider.get(f"result:{task_id}")
        if data is None:
            return None
        return json.loads(data)


def parse_conn_string(conn_string):
    """
    Parse Redis connection string
    """
    try:
        split_conn_string = conn_string.partition(":")
        redis_host = split_conn_string[0]
        redis_port = int(split_conn_string[2].split(",")[0])
        redis_pw = split_conn_string[2].split(",")[1].replace("password=", "")
        return f"rediss://:{redis_pw}@{redis_host}:{redis_port}/0?ssl_cert_reqs=required"
    except (ValueError, IndexError):
        return conn_string


def get_storage() -> TempStorage:
    """
    Get temporary storage
    """
    connection_string = parse_conn_string(os.environ.get("REDIS_CONNECTION",
                                                         "redis://127.0.0.1:6379"))
    temp_store = TempStorage.create_with_redis(connection_string)
    return temp_store
