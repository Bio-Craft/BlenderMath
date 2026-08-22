"""Small, deterministic expression evaluator for mathematical plots."""

from __future__ import annotations

import ast
import math
from collections.abc import Mapping


class ExpressionError(ValueError):
    pass


_FUNCTIONS = {
    name: getattr(math, name)
    for name in (
        "acos", "asin", "atan", "atan2", "ceil", "cos", "cosh", "exp",
        "floor", "hypot", "log", "log10", "sin", "sinh", "sqrt", "tan", "tanh",
    )
}
_FUNCTIONS.update({"abs": abs, "max": max, "min": min, "pow": pow})
_CONSTANTS = {"e": math.e, "pi": math.pi, "tau": math.tau}
_ALLOWED = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load,
    ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.USub, ast.UAdd,
)


class Expression:
    """Compile and evaluate a restricted scalar mathematical expression."""

    def __init__(self, source: str):
        self.source = source.strip()
        if not self.source:
            raise ExpressionError("Expression cannot be empty")
        try:
            tree = ast.parse(self.source, mode="eval")
        except SyntaxError as exc:
            raise ExpressionError(str(exc)) from exc
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED):
                raise ExpressionError(f"Unsupported syntax: {type(node).__name__}")
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
                    raise ExpressionError("Only built-in math functions are allowed")
                if node.keywords:
                    raise ExpressionError("Keyword arguments are not allowed")
        self._names = frozenset(
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        ) - _FUNCTIONS.keys() - _CONSTANTS.keys()
        self._code = compile(tree, "<BlenderMath expression>", "eval")

    @property
    def variables(self) -> frozenset[str]:
        return self._names

    def __call__(self, **variables: float) -> float:
        missing = self._names - variables.keys()
        if missing:
            raise ExpressionError(f"Missing variables: {', '.join(sorted(missing))}")
        namespace: Mapping[str, object] = _FUNCTIONS | _CONSTANTS | variables
        try:
            return float(eval(self._code, {"__builtins__": {}}, namespace))
        except (ArithmeticError, TypeError, ValueError) as exc:
            raise ExpressionError(str(exc)) from exc

    def sample(self, variable: str, start: float, end: float, count: int, **parameters: float):
        if count < 2:
            raise ValueError("count must be at least 2")
        step = (end - start) / (count - 1)
        return [
            (value, self(**parameters, **{variable: value}))
            for index in range(count)
            for value in [start + index * step]
        ]
