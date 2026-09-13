"""Layout generator - creates responsive grid layouts for dashboard widgets."""

from __future__ import annotations

from typing import Any

# Widget size presets by type
WIDGET_SIZES: dict[str, dict[str, int]] = {
    "kpi": {"w": 3, "h": 2},
    "line": {"w": 6, "h": 4},
    "bar": {"w": 6, "h": 4},
    "area": {"w": 6, "h": 4},
    "pie": {"w": 4, "h": 4},
    "donut": {"w": 4, "h": 4},
    "scatter": {"w": 6, "h": 4},
    "heatmap": {"w": 6, "h": 4},
    "treemap": {"w": 6, "h": 4},
    "gauge": {"w": 4, "h": 3},
    "table": {"w": 12, "h": 5},
    "pivot": {"w": 12, "h": 5},
    "map": {"w": 8, "h": 5},
    "timeline": {"w": 12, "h": 4},
    "text": {"w": 12, "h": 2},
    "forecast": {"w": 8, "h": 4},
}

GRID_COLS = 12
GRID_ROW_HEIGHT = 80  # px


class LayoutGenerator:
    """Generates responsive grid layouts for dashboard widgets."""

    def __init__(self, cols: int = GRID_COLS) -> None:
        self.cols = cols

    def generate_layout(
        self,
        widgets: list[dict[str, Any]],
        breakpoint: str = "desktop",
    ) -> dict[str, Any]:
        """Generate a complete layout for the given widgets."""
        positions = self._compute_positions(widgets, breakpoint)

        return {
            "breakpoint": breakpoint,
            "cols": self.cols,
            "row_height": GRID_ROW_HEIGHT,
            "positions": positions,
            "responsive": {
                "desktop": self._compute_positions(widgets, "desktop"),
                "tablet": self._compute_positions(widgets, "tablet"),
                "mobile": self._compute_positions(widgets, "mobile"),
            },
        }

    def _compute_positions(
        self,
        widgets: list[dict[str, Any]],
        breakpoint: str,
    ) -> list[dict[str, Any]]:
        """Compute non-overlapping positions for all widgets."""
        cols = self._cols_for_breakpoint(breakpoint)
        positions: list[dict[str, Any]] = []
        occupied: list[tuple[int, int, int, int]] = []  # (x, y, w, h)

        sorted_widgets = sorted(
            widgets,
            key=lambda w: self._priority(w.get("type", "kpi")),
        )

        for widget in sorted_widgets:
            w_type = widget.get("type", "kpi")
            size = WIDGET_SIZES.get(w_type, {"w": 4, "h": 3})

            w = min(size["w"], cols)
            h = size["h"]

            if breakpoint == "tablet":
                w = min(w, 6)
            elif breakpoint == "mobile":
                w = cols

            x, y = self._find_position(cols, w, h, occupied)
            occupied.append((x, y, w, h))

            positions.append(
                {
                    "widget_id": widget.get("id", ""),
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                }
            )

        return positions

    def _find_position(
        self,
        cols: int,
        w: int,
        h: int,
        occupied: list[tuple[int, int, int, int]],
    ) -> tuple[int, int]:
        """Find the first available position in the grid."""
        for y in range(100):
            for x in range(0, cols - w + 1):
                if not self._overlaps(x, y, w, h, occupied):
                    return x, y
        return 0, len(occupied) * 3

    def _overlaps(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        occupied: list[tuple[int, int, int, int]],
    ) -> bool:
        for ox, oy, ow, oh in occupied:
            if x < ox + ow and x + w > ox and y < oy + oh and y + h > oy:
                return True
        return False

    def _cols_for_breakpoint(self, breakpoint: str) -> int:
        return {"desktop": 12, "tablet": 8, "mobile": 4}.get(breakpoint, 12)

    def _priority(self, widget_type: str) -> int:
        order = {
            "kpi": 0,
            "gauge": 1,
            "text": 2,
            "line": 10,
            "bar": 11,
            "area": 12,
            "pie": 13,
            "donut": 14,
            "scatter": 15,
            "heatmap": 16,
            "treemap": 17,
            "forecast": 18,
            "timeline": 20,
            "table": 30,
            "pivot": 31,
            "map": 25,
        }
        return order.get(widget_type, 99)
