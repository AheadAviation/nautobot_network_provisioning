"""
Proxy Worker Client for communicating with remote Celery workers.

This module enables Nautobot to dispatch tasks to a remote Celery worker
running on a proxy/jump host that has network access to managed devices.

The proxy worker architecture allows:
- Nautobot to remain in a secure zone without direct device access
- A proxy worker to bridge between Nautobot and the device network
- Tasks like MAC/ARP collection to be executed via the proxy

Configuration is done via Django settings or environment variables:
    PROXY_WORKER_BROKER_URL: Redis URL for the proxy worker broker
    PROXY_WORKER_ENABLED: Enable/disable proxy worker functionality
"""

import os
import logging
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class ProxyWorkerConfig:
    """Configuration for the proxy worker connection."""
    
    broker_url: str
    backend_url: str
    queue_name: str
    enabled: bool
    timeout: int  # Task timeout in seconds
    
    @classmethod
    def from_settings(cls) -> "ProxyWorkerConfig":
        """Load configuration from Django settings or environment."""
        # Get from plugin config or environment
        plugin_config = getattr(settings, "PLUGINS_CONFIG", {}).get("nautobot_network_provisioning", {})
        
        broker_url = plugin_config.get(
            "proxy_broker_url",
            os.getenv("PROXY_WORKER_BROKER_URL", "redis://172.20.12.50:6379/0")
        )
        backend_url = plugin_config.get(
            "proxy_backend_url",
            os.getenv("PROXY_WORKER_BACKEND_URL", broker_url)
        )
        queue_name = plugin_config.get(
            "proxy_queue_name",
            os.getenv("PROXY_WORKER_QUEUE", "proxy_queue")
        )
        enabled = plugin_config.get(
            "proxy_worker_enabled",
            os.getenv("PROXY_WORKER_ENABLED", "true").lower() in ("true", "1", "yes")
        )
        timeout = int(plugin_config.get(
            "proxy_task_timeout",
            os.getenv("PROXY_TASK_TIMEOUT", "120")
        ))
        
        return cls(
            broker_url=broker_url,
            backend_url=backend_url,
            queue_name=queue_name,
            enabled=enabled,
            timeout=timeout,
        )


class ProxyWorkerClient:
    """
    Client for dispatching tasks to the remote proxy Celery worker.
    
    This creates a separate Celery app instance that connects to the
    proxy worker's Redis broker, allowing Nautobot to send tasks.
    """
    
    _instance: Optional["ProxyWorkerClient"] = None
    _celery_app = None
    
    def __new__(cls):
        """Singleton pattern to reuse Celery connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.config = ProxyWorkerConfig.from_settings()
        self._initialized = True
        
        if self.config.enabled:
            self._init_celery()
    
    def _init_celery(self):
        """Initialize the Celery app for the proxy worker."""
        try:
            from celery import Celery
            
            self._celery_app = Celery(
                "nautobot_proxy_client",
                broker=self.config.broker_url,
                backend=self.config.backend_url,
            )
            
            self._celery_app.conf.update(
                task_serializer="json",
                accept_content=["json"],
                result_serializer="json",
                timezone="UTC",
                enable_utc=True,
                # Don't try to autodiscover tasks - we're just a client
                task_always_eager=False,
                task_default_queue=self.config.queue_name,
            )
            
            logger.info(
                f"Proxy worker client initialized: broker={self.config.broker_url}, "
                f"queue={self.config.queue_name}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize proxy worker client: {e}")
            self._celery_app = None
    
    @property
    def is_available(self) -> bool:
        """Check if the proxy worker client is available."""
        return self.config.enabled and self._celery_app is not None
    
    def send_task(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: dict = None,
        timeout: int = None,
    ) -> Any:
        """
        Send a task to the proxy worker and wait for result.
        
        Args:
            task_name: Name of the task (e.g., "proxy.execute_command")
            args: Positional arguments for the task
            kwargs: Keyword arguments for the task
            timeout: Override the default timeout
            
        Returns:
            The task result
            
        Raises:
            RuntimeError: If the proxy worker is not available
            TimeoutError: If the task times out
        """
        if not self.is_available:
            raise RuntimeError("Proxy worker client is not available")
        
        kwargs = kwargs or {}
        timeout = timeout or self.config.timeout
        
        logger.debug(f"Sending task {task_name} to proxy worker with timeout={timeout}s")
        
        result = self._celery_app.send_task(
            task_name,
            args=args,
            kwargs=kwargs,
            queue=self.config.queue_name,
        )
        
        try:
            return result.get(timeout=timeout)
        except Exception as e:
            logger.error(f"Proxy task {task_name} failed: {e}")
            raise
    
    def send_task_async(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: dict = None,
    ):
        """
        Send a task to the proxy worker without waiting for result.
        
        Returns the AsyncResult object for later inspection.
        """
        if not self.is_available:
            raise RuntimeError("Proxy worker client is not available")
        
        kwargs = kwargs or {}
        
        logger.debug(f"Sending async task {task_name} to proxy worker")
        
        return self._celery_app.send_task(
            task_name,
            args=args,
            kwargs=kwargs,
            queue=self.config.queue_name,
        )


# Convenience functions for common proxy tasks

def get_proxy_client() -> ProxyWorkerClient:
    """Get the singleton proxy worker client instance."""
    return ProxyWorkerClient()


def proxy_execute_command(
    host: str,
    username: str,
    password: str,
    command: str,
    device_type: str = "cisco_ios",
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Execute a command on a device via the proxy worker.
    
    Args:
        host: Device IP or hostname
        username: SSH username
        password: SSH password
        command: Command to execute
        device_type: Netmiko device type
        timeout: Command timeout
        
    Returns:
        Dict with 'success' and 'output' keys
    """
    client = get_proxy_client()
    return client.send_task(
        "proxy.execute_command",
        args=(host, username, password, command, device_type),
        timeout=timeout,
    )


def proxy_get_mac_table(
    host: str,
    username: str,
    password: str,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Get MAC address table from a device via proxy."""
    client = get_proxy_client()
    return client.send_task(
        "proxy.get_mac_table",
        args=(host, username, password),
        timeout=timeout,
    )


def proxy_get_arp_table(
    host: str,
    username: str,
    password: str,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Get ARP table from a device via proxy."""
    client = get_proxy_client()
    return client.send_task(
        "proxy.get_arp_table",
        args=(host, username, password),
        timeout=timeout,
    )


def proxy_ping(host: str, timeout: int = 60) -> Dict[str, Any]:
    """Ping a host via the proxy worker."""
    client = get_proxy_client()
    return client.send_task(
        "proxy.ping",
        args=(host,),
        timeout=timeout,
    )


def test_proxy_connection() -> Tuple[bool, str]:
    """
    Test if the proxy worker is reachable and responding.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        client = get_proxy_client()
        
        if not client.is_available:
            return False, "Proxy worker client is not enabled or failed to initialize"
        
        # Try to ping a known host (the proxy itself)
        result = proxy_ping("127.0.0.1", timeout=30)
        
        if result.get("success"):
            return True, "Proxy worker is connected and responding"
        else:
            return False, f"Proxy worker responded but ping failed: {result.get('error', 'unknown')}"
            
    except TimeoutError:
        return False, "Proxy worker connection timed out"
    except Exception as e:
        return False, f"Proxy worker connection failed: {str(e)}"
