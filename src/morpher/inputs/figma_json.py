import json
from pathlib import Path
from typing import Any

from morpher.ir.nodes import DesignDocument, DesignNode
from morpher.ir.styles import DesignStyle


_CONTAINER_TYPES = {"FRAME", "GROUP", "SECTION", "COMPONENT", "INSTANCE"}
_GEOMETRY_EPSILON = 1e-3
_GEOMETRY_PRECISION = 6


class FigmaJsonAdapter:
    """Load Figma JSON_REST_V1 payloads into Morpher's shared Design IR."""

    extensions = (".json",)

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def load(self, path: Path) -> DesignDocument:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return self.from_data(data)

    def from_data(self, data: dict[str, Any]) -> DesignDocument:
        document = data.get("document")
        if not isinstance(document, dict):
            raise ValueError("Figma JSON must contain a 'document' object")

        warnings: list[str] = []
        root = self._normalize_node(document, warnings)
        return DesignDocument(
            root=root,
            warnings=warnings,
            schema_version=data.get("schemaVersion"),
        )

    def _normalize_node(self, node: dict[str, Any], warnings: list[str]) -> DesignNode:
        source_type = str(node.get("type", "UNKNOWN"))
        kind = self._kind_for(node)

        if kind == "unsupported":
            warnings.append(
                f"Unsupported Figma node type {source_type!r} at {node.get('id', '<unknown>')} ({node.get('name', 'unnamed')})"
            )

        children = []
        if kind != "icon" or source_type == "VECTOR":
            children = [
                self._normalize_node(child, warnings)
                for child in node.get("children", [])
                if isinstance(child, dict)
            ]

        return DesignNode(
            kind=kind,
            name=node.get("name"),
            source_id=node.get("id"),
            source_type=source_type,
            text=node.get("characters") if source_type == "TEXT" else None,
            image_ref=self._image_ref(node),
            style=self._style(node),
            children=children,
        )

    def _kind_for(self, node: dict[str, Any]) -> str:
        source_type = node.get("type")
        if source_type == "VECTOR" or self._is_vector_composite(node):
            return "icon"
        if source_type in _CONTAINER_TYPES:
            return "container"
        if source_type == "TEXT":
            return "text"
        if source_type == "LINE":
            return "divider"
        if source_type == "RECTANGLE":
            return "image" if self._image_ref(node) else "shape"
        return "unsupported"

    @staticmethod
    def _is_vector_composite(node: dict[str, Any]) -> bool:
        children = node.get("children")
        return (
            node.get("type") in _CONTAINER_TYPES
            and isinstance(children, list)
            and bool(children)
            and all(isinstance(child, dict) and child.get("type") == "VECTOR" for child in children)
        )

    @staticmethod
    def _image_ref(node: dict[str, Any]) -> str | None:
        for fill in node.get("fills", []):
            if isinstance(fill, dict) and fill.get("type") == "IMAGE":
                value = fill.get("imageRef")
                return str(value) if value else None
        return None

    @classmethod
    def _image_opacity(cls, node: dict[str, Any]) -> float | None:
        for fill in node.get("fills", []):
            if isinstance(fill, dict) and fill.get("type") == "IMAGE" and fill.get("visible") is not False:
                return cls._number(fill.get("opacity")) or 1.0
        return None

    def _style(self, node: dict[str, Any]) -> DesignStyle:
        box = node.get("absoluteBoundingBox") or {}
        constraints = node.get("constraints") or {}
        text_style = node.get("style") or {}
        layout_mode = node.get("layoutMode")
        source_type = node.get("type")
        solid_color = self._solid_color(node)

        return DesignStyle(
            width=self._geometry_number(box.get("width")),
            height=self._geometry_number(box.get("height")),
            x=self._geometry_number(box.get("x")),
            y=self._geometry_number(box.get("y")),
            rotation=self._geometry_number(node.get("rotation")),
            gap=self._geometry_number(node.get("itemSpacing")),
            padding_top=self._geometry_number(node.get("paddingTop")),
            padding_right=self._geometry_number(node.get("paddingRight")),
            padding_bottom=self._geometry_number(node.get("paddingBottom")),
            padding_left=self._geometry_number(node.get("paddingLeft")),
            opacity=self._number(node.get("opacity")),
            image_opacity=self._image_opacity(node),
            background=None if source_type == "TEXT" else solid_color,
            text_color=solid_color if source_type == "TEXT" else None,
            stroke_color=self._solid_stroke_color(node),
            stroke_weight=self._geometry_number(node.get("strokeWeight")),
            border_radius=self._geometry_number(node.get("cornerRadius")),
            layout_direction=self._layout_direction(layout_mode),
            width_mode=self._sizing_mode(node.get("layoutSizingHorizontal")),
            height_mode=self._sizing_mode(node.get("layoutSizingVertical")),
            primary_axis_align=self._layout_alignment(node.get("primaryAxisAlignItems")),
            counter_axis_align=self._layout_alignment(node.get("counterAxisAlignItems")),
            layout_align=self._layout_alignment(node.get("layoutAlign")),
            layout_grow=self._geometry_number(node.get("layoutGrow")),
            constraint_horizontal=constraints.get("horizontal"),
            constraint_vertical=constraints.get("vertical"),
            font_family=text_style.get("fontFamily"),
            font_postscript_name=text_style.get("fontPostScriptName"),
            font_style=text_style.get("fontStyle"),
            font_weight=self._integer(text_style.get("fontWeight")),
            font_size=self._geometry_number(text_style.get("fontSize")),
            letter_spacing=self._geometry_number(text_style.get("letterSpacing")),
            line_height=self._geometry_number(text_style.get("lineHeightPx")),
            text_align_horizontal=text_style.get("textAlignHorizontal"),
            text_align_vertical=text_style.get("textAlignVertical"),
        )

    @staticmethod
    def _layout_direction(value: Any):
        if value == "HORIZONTAL":
            return "horizontal"
        if value == "VERTICAL":
            return "vertical"
        return None

    @staticmethod
    def _sizing_mode(value: Any):
        mapping = {
            "FIXED": "fixed",
            "HUG": "hug",
            "FILL": "fill",
        }
        return mapping.get(value)

    @staticmethod
    def _layout_alignment(value: Any) -> str | None:
        if isinstance(value, str) and value:
            return value.lower()
        return None

    @staticmethod
    def _paint_color(paint: dict[str, Any]) -> str | None:
        if paint.get("type") != "SOLID" or paint.get("visible") is False:
            return None
        color = paint.get("color") or {}
        if not all(channel in color for channel in ("r", "g", "b")):
            return None
        r = round(float(color["r"]) * 255)
        g = round(float(color["g"]) * 255)
        b = round(float(color["b"]) * 255)
        alpha = float(color.get("a", 1)) * float(paint.get("opacity", 1))
        return f"rgba({r}, {g}, {b}, {alpha:g})"

    @classmethod
    def _solid_color(cls, node: dict[str, Any]) -> str | None:
        for fill in node.get("fills", []):
            if isinstance(fill, dict):
                color = cls._paint_color(fill)
                if color:
                    return color
        return None

    @classmethod
    def _solid_stroke_color(cls, node: dict[str, Any]) -> str | None:
        for stroke in node.get("strokes", []):
            if isinstance(stroke, dict):
                color = cls._paint_color(stroke)
                if color:
                    return color
        return None

    @staticmethod
    def _number(value: Any) -> float | None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return None

    @classmethod
    def _geometry_number(cls, value: Any) -> float | None:
        number = cls._number(value)
        if number is None:
            return None
        if abs(number) < _GEOMETRY_EPSILON:
            return 0.0
        return round(number, _GEOMETRY_PRECISION)

    @staticmethod
    def _integer(value: Any) -> int | None:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, float):
            return int(value)
        return None
