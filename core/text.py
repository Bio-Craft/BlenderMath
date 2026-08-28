"""Semantic math objects and optional Typst backend protocol."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .mobject import MObject, Style, VGroup
from .colors import WHITE


class Text(MObject):
    """Lightweight label compiled to a native Blender text curve."""

    kind = "text"

    def __init__(self, text: str, *, font_size=0.28, style=None, name=None):
        super().__init__(name or f"Text {text}", style=style or Style(color=(0.9, 0.92, 0.96, 1.0)))
        self.text = str(text)
        self.font_size = float(font_size)
        self.geometry.update(text=self.text, font_size=self.font_size)


@dataclass(frozen=True)
class MathToken:
    source: str
    occurrence: int

    @property
    def key(self):
        return self.source, self.occurrence


@dataclass(frozen=True)
class MathPart:
    """A rendered source span that can participate in semantic transforms."""

    source: str
    occurrence: int
    start: int
    end: int

    @property
    def key(self):
        return self.source, self.occurrence


class MathTex(VGroup):
    """Semantic Typst source; geometry is supplied by an installed backend."""

    kind = "math"

    def __init__(
        self,
        source: str,
        *,
        substrings_to_isolate=(),
        representation: str = "GREASE_PENCIL",
        stroke_mode: str = "NONE",
        style: Style | None = None,
        name="MathTex",
    ):
        super().__init__(name=name)
        self.style = style or Style(
            color=WHITE, fill_color=WHITE, fill_opacity=1.0,
        )
        representation = representation.upper()
        if representation not in {"GREASE_PENCIL", "CURVE", "MESH"}:
            raise ValueError("MathTex representation must be GREASE_PENCIL, CURVE, or MESH")
        stroke_mode = stroke_mode.upper()
        if stroke_mode not in {"NONE", "MATCH_FILL", "BLACK"}:
            raise ValueError("MathTex stroke_mode must be NONE, MATCH_FILL, or BLACK")
        self.source = source
        self.representation = representation
        self.stroke_mode = stroke_mode
        self.substrings_to_isolate = tuple(substrings_to_isolate)
        self.tokens = self._tokenize(source)
        self.parts = self._find_matching_parts(source, self.substrings_to_isolate)
        self.token_colors: dict[tuple[str, int | None], tuple[float, float, float, float]] = {}
        self.metadata["typst_source"] = source
        self.metadata["representation"] = representation

    @staticmethod
    def _tokenize(source):
        semantic_source = " ".join(
            source[start:end]
            for start, end in MathTex._automatic_semantic_ranges(source)
        )
        pieces = re.findall(
            r"[A-Za-z]+|\d+|\^|_|[+\-*/=()]|[^\s]",
            semantic_source.strip("$ "),
        )
        counts = {}
        result = []
        for piece in pieces:
            occurrence = counts.get(piece, 0)
            counts[piece] = occurrence + 1
            result.append(MathToken(piece, occurrence))
        return result

    def matching_tokens(self, other: "MathTex"):
        right = {token.key: token for token in other.tokens}
        return [(token, right[token.key]) for token in self.tokens if token.key in right]

    @staticmethod
    def _layout_ranges(source):
        """Return spans whose Typst separators must remain in math mode."""
        ranges = []
        pattern = re.compile(r"\b(?:mat|vec|cases|stack)\s*\(")
        for match in pattern.finditer(source):
            depth = 0
            for index in range(match.end() - 1, len(source)):
                if source[index] == "(":
                    depth += 1
                elif source[index] == ")":
                    depth -= 1
                    if depth == 0:
                        ranges.append((match.start(), index + 1))
                        break
        return tuple(ranges)

    @staticmethod
    def _automatic_semantic_ranges(source):
        """Limit automatic math semantics inside rich Typst source to `$...$`."""
        if not source.lstrip().startswith("#"):
            return ((0, len(source)),)

        ranges = []
        start = None
        for index, character in enumerate(source):
            if character != "$" or (index > 0 and source[index - 1] == "\\"):
                continue
            if start is None:
                start = index + 1
            else:
                ranges.append((start, index))
                start = None
        return tuple(ranges)

    @staticmethod
    def _inside_ranges(start, end, ranges):
        return any(start < range_end and end > range_start for range_start, range_end in ranges)

    @staticmethod
    def _find_matching_parts(source, isolated):
        """Find non-overlapping Typst spans while leaving layout syntax intact."""
        spans = []
        occupied = [False] * len(source)
        layout_ranges = MathTex._layout_ranges(source)
        semantic_ranges = MathTex._automatic_semantic_ranges(source)

        # Explicit terms win over their component variables. This is useful for
        # constructs such as sqrt(...) that should travel as one visual term.
        for text in sorted({str(item) for item in isolated if str(item)}, key=len, reverse=True):
            for match in re.finditer(re.escape(text), source):
                if MathTex._inside_ranges(match.start(), match.end(), layout_ranges):
                    continue
                if any(occupied[match.start():match.end()]):
                    continue
                spans.append((match.start(), match.end(), text))
                occupied[match.start():match.end()] = [True] * len(text)

        # Single-letter variables, numbers, and common relation/arithmetic
        # symbols are safe to wrap in Typst without changing expression syntax.
        auto_pattern = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]|\d+|[+\-=])(?![A-Za-z0-9])")
        for match in auto_pattern.finditer(source):
            if not MathTex._inside_ranges(match.start(), match.end(), semantic_ranges):
                continue
            if MathTex._inside_ranges(match.start(), match.end(), layout_ranges):
                continue
            if any(occupied[match.start():match.end()]):
                continue
            if match.group(0).isalpha() and re.match(r"\s*\(", source[match.end():]):
                continue
            spans.append((match.start(), match.end(), match.group(0)))

        counts = {}
        parts = []
        for start, end, text in sorted(spans):
            occurrence = counts.get(text, 0)
            counts[text] = occurrence + 1
            parts.append(MathPart(text, occurrence, start, end))
        return tuple(parts)

    def matching_parts(self, other: "MathTex", key_map=None):
        """Return source/target part pairs, respecting occurrence order."""
        key_map = key_map or {}
        right = {part.key: part for part in other.parts}
        matches = []
        for part in self.parts:
            target_source = key_map.get(part.source, part.source)
            target = right.get((target_source, part.occurrence))
            if target is not None:
                matches.append((part, target))
        return matches

    def get_tokens(self, source: str) -> tuple[MathToken, ...]:
        """Return semantic source tokens before Blender glyph compilation."""
        return tuple(token for token in self.tokens if token.source == source)

    def set_color_by_token(self, source: str, color, occurrence: int | None = None) -> "MathTex":
        if not self.get_tokens(source):
            raise KeyError(f"Token not found: {source}")
        rgba = tuple(float(component) for component in color)
        if len(rgba) == 3:
            rgba += (1.0,)
        if len(rgba) != 4:
            raise ValueError("color must have 3 or 4 components")
        self.token_colors[(source, occurrence)] = rgba  # type: ignore[assignment]
        return self

    def render_source(self) -> str:
        """Instrument selected tokens with Typst colors before compilation."""
        result = self.source
        for (source, occurrence), color in self.token_colors.items():
            hex_color = "#" + "".join(f"{round(component * 255):02x}" for component in color[:3])
            replacement = f'#text(fill: rgb("{hex_color}"))[$ {source} $]'
            # Typst's `_` and `^` delimit subscripts/superscripts rather than
            # extending a math identifier, so only letters/digits block a match.
            pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(source)}(?![A-Za-z0-9])")
            index = -1
            layout_ranges = self._layout_ranges(result)
            semantic_ranges = self._automatic_semantic_ranges(result)

            def replace(match):
                nonlocal index
                if not self._inside_ranges(match.start(), match.end(), semantic_ranges):
                    return match.group(0)
                if self._inside_ranges(match.start(), match.end(), layout_ranges):
                    return match.group(0)
                index += 1
                if re.match(r"\s*\(", match.string[match.end():]):
                    raise ValueError(
                        f"Token {source!r} is used as a Typst function; isolate the full expression before coloring"
                    )
                if occurrence is not None and index != occurrence:
                    return match.group(0)
                return f"({replacement})" if match.start() > 0 and match.string[match.start() - 1] in "^_" else replacement

            result = pattern.sub(replace, result)
        return result

    def render_source_with_part_ids(self):
        """Return Typst source with temporary colors identifying matchable parts."""
        if not self.parts:
            return self.render_source(), {}
        source = self.source
        layout_ranges = self._layout_ranges(source)
        semantic_ranges = self._automatic_semantic_ranges(source)
        identifiers = {}
        replacements = []
        occupied = [False] * len(source)
        for index, part in enumerate(self.parts):
            # A compact 12x12x12 color cube gives stable, exact SVG material
            # colors while staying away from the normal black/white defaults.
            value = index
            rgb = (
                32 + 16 * (value % 12),
                32 + 16 * ((value // 12) % 12),
                32 + 16 * ((value // 144) % 12),
            )
            hex_color = "#" + "".join(f"{component:02x}" for component in rgb)
            identifiers[rgb] = part.key
            replacement = f'#text(fill: rgb("{hex_color}"))[$ {part.source} $]'
            if part.start > 0 and source[part.start - 1] in "^_":
                replacement = f"({replacement})"
            replacements.append((part.start, part.end, replacement))
            occupied[part.start:part.end] = [True] * (part.end - part.start)

        # Preserve semantic colors on non-matching constructs (for example an
        # integral glyph). Matching parts recover their requested color in the
        # Blender compiler after the temporary identifier has been read.
        for (token, selected_occurrence), color in self.token_colors.items():
            hex_color = "#" + "".join(f"{round(component * 255):02x}" for component in color[:3])
            pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])")
            occurrence = -1
            for match in pattern.finditer(source):
                if not self._inside_ranges(match.start(), match.end(), semantic_ranges):
                    continue
                occurrence += 1
                if selected_occurrence is not None and occurrence != selected_occurrence:
                    continue
                if any(occupied[match.start():match.end()]):
                    continue
                if self._inside_ranges(match.start(), match.end(), layout_ranges):
                    continue
                if re.match(r"\s*\(", source[match.end():]):
                    raise ValueError(
                        f"Token {token!r} is used as a Typst function; isolate the full expression before coloring"
                    )
                replacement = f'#text(fill: rgb("{hex_color}"))[$ {token} $]'
                if match.start() > 0 and source[match.start() - 1] in "^_":
                    replacement = f"({replacement})"
                replacements.append((match.start(), match.end(), replacement))
        for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
            source = source[:start] + replacement + source[end:]
        return source, identifiers


Math = MathTex
