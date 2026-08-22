"""Discovery bridge for blender_typst_importer across extension repositories."""

from __future__ import annotations

from importlib import import_module

import bpy


def resolve_typst_express():
    """Return typst_express from legacy or Blender Extension namespaces."""
    candidates = ["typst_importer.typst_to_svg"]
    repos = getattr(getattr(bpy.context.preferences, "extensions", None), "repos", ())
    candidates.extend(
        f"bl_ext.{repo.module}.typst_importer.typst_to_svg"
        for repo in repos
        if getattr(repo, "module", None)
    )
    errors = []
    for module_name in candidates:
        try:
            module = import_module(module_name)
        except (ImportError, ModuleNotFoundError) as exc:
            errors.append(f"{module_name}: {exc}")
            continue
        function = getattr(module, "typst_express", None)
        if function is not None:
            return function
        errors.append(f"{module_name}: typst_express is not exported")
    detail = "\n".join(errors)
    raise RuntimeError(
        "MathTex requires blender_typst_importer with the typst_express API. "
        f"Searched all configured extension repositories.\n{detail}"
    )
