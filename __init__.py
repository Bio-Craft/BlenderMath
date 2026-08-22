"""BlenderMath add-on entry point."""

import sys

from .addon import register, unregister
from . import core as _core

# Text Editor scenes can use the concise public DSL regardless of Blender's
# extension package namespace (bl_ext.<repo>.blendermath).
sys.modules.setdefault("bmath", _core)

bl_info = {
    "name": "BlenderMath",
    "author": "BioCraft",
    "description": "Math, simulation, and scientific visualization toolkit",
    "blender": (4, 2, 0),
    "version": (0, 1, 0),
    "location": "View3D > Sidebar > BlenderMath",
    "category": "Animation",
}

__all__ = ["register", "unregister"]
