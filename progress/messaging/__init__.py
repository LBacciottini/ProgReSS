"""
This package provides the services required to manage classical communications between devices.
"""

from progress.messaging.messages import ClassicalRoutingTableMessage
from progress.messaging.router import MessageRoutingService

__all__ = ["ClassicalRoutingTableMessage", "MessageRoutingService"]
