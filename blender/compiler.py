"""Compatibility import for the versioned Blender backend."""

from ..backend.blender_52.compiler import BlenderCompiler, compile_scene

__all__ = ["BlenderCompiler", "compile_scene"]
