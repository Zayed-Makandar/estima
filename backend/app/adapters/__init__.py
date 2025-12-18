from .robu import robu_adapter
from .robocraze import robocraze_adapter
from .thinkrobotics import thinkrobotics_adapter
from .evelta import evelta_adapter

ALL_ADAPTERS = {
    "robu": robu_adapter,
    "robocraze": robocraze_adapter,
    "thinkrobotics": thinkrobotics_adapter,
    "evelta": evelta_adapter,
}

__all__ = ["ALL_ADAPTERS"]

