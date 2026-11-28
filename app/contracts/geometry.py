"""Pure-math coordinate transform utilities (CORE-02 Geometry Law).

Coordinates Invariant:
- Stored in DB & sent to FE viewer: visual (rotated) top-left CropBox coordinates
  (x0, y0, x1, y1) where 0 <= x0 < x1 <= visual_width, 0 <= y0 < y1 <= visual_height.
- Used inside PDF redaction (PyMuPDF add_redact_annot): unrotated CropBox coordinates.
- Rotation is one of: 0, 90, 180, 270 degrees clockwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class VisualRect:
    """A bounding rectangle in visual (rotated) top-left CropBox coordinates."""
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if self.x0 > self.x1 or self.y0 > self.y1:
            raise ValueError(f"Invalid rectangle bounds: ({self.x0}, {self.y0}, {self.x1}, {self.y1})")

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def as_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

    def intersects(self, other: VisualRect) -> bool:
        return not (self.x1 <= other.x0 or self.x0 >= other.x1 or self.y1 <= other.y0 or self.y0 >= other.y1)

    def iou(self, other: VisualRect) -> float:
        ix0 = max(self.x0, other.x0)
        iy0 = max(self.y0, other.y0)
        ix1 = min(self.x1, other.x1)
        iy1 = min(self.y1, other.y1)
        if ix1 <= ix0 or iy1 <= iy0:
            return 0.0
        intersection = (ix1 - ix0) * (iy1 - iy0)
        union = (self.width * self.height) + (other.width * other.height) - intersection
        return intersection / union if union > 0 else 0.0


@dataclass(frozen=True)
class UnrotRect:
    """A bounding rectangle in unrotated PDF CropBox coordinates."""
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if self.x0 > self.x1 or self.y0 > self.y1:
            raise ValueError(f"Invalid unrotated bounds: ({self.x0}, {self.y0}, {self.x1}, {self.y1})")

    def as_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)


def visual_to_unrot_rect(
    visual_rect: VisualRect | Tuple[float, float, float, float],
    unrot_width: float,
    unrot_height: float,
    rotation_deg: int = 0,
) -> UnrotRect:
    """Convert visual (rotated) top-left CropBox rect to unrotated CropBox rect.

    Args:
        visual_rect: (x0, y0, x1, y1) in visual top-left coordinates.
        unrot_width: Width of the unrotated page in points (W).
        unrot_height: Height of the unrotated page in points (H).
        rotation_deg: Clockwise rotation in degrees (0, 90, 180, 270).

    Returns:
        UnrotRect in unrotated space.
    """
    if isinstance(visual_rect, (tuple, list)):
        vx0, vy0, vx1, vy1 = visual_rect
    else:
        vx0, vy0, vx1, vy1 = visual_rect.x0, visual_rect.y0, visual_rect.x1, visual_rect.y1

    rot = rotation_deg % 360

    if rot == 0:
        ux0, uy0, ux1, uy1 = vx0, vy0, vx1, vy1
    elif rot == 90:
        # 90 deg CW: visual_w = unrot_h, visual_h = unrot_w
        # Forward: vx = H - uy, vy = ux
        # Inverse: ux = vy, uy = H - vx
        ux0 = vy0
        uy0 = unrot_height - vx1
        ux1 = vy1
        uy1 = unrot_height - vx0
    elif rot == 180:
        # 180 deg CW: visual_w = unrot_w, visual_h = unrot_h
        # Forward: vx = W - ux, vy = H - uy
        # Inverse: ux = W - vx, uy = H - vy
        ux0 = unrot_width - vx1
        uy0 = unrot_height - vy1
        ux1 = unrot_width - vx0
        uy1 = unrot_height - vy0
    elif rot == 270:
        # 270 deg CW: visual_w = unrot_h, visual_h = unrot_w
        # Forward: vx = uy, vy = W - ux
        # Inverse: ux = W - vy, uy = vx
        ux0 = unrot_width - vy1
        uy0 = vx0
        ux1 = unrot_width - vy0
        uy1 = vx1
    else:
        raise ValueError(f"Unsupported rotation angle: {rotation_deg}. Must be 0, 90, 180, or 270.")

    min_x, max_x = min(ux0, ux1), max(ux0, ux1)
    min_y, max_y = min(uy0, uy1), max(uy0, uy1)
    return UnrotRect(min_x, min_y, max_x, max_y)


def unrot_to_visual_rect(
    unrot_rect: UnrotRect | Tuple[float, float, float, float],
    unrot_width: float,
    unrot_height: float,
    rotation_deg: int = 0,
) -> VisualRect:
    """Convert unrotated CropBox rect to visual (rotated) top-left CropBox rect."""
    if isinstance(unrot_rect, (tuple, list)):
        ux0, uy0, ux1, uy1 = unrot_rect
    else:
        ux0, uy0, ux1, uy1 = unrot_rect.x0, unrot_rect.y0, unrot_rect.x1, unrot_rect.y1

    rot = rotation_deg % 360

    if rot == 0:
        vx0, vy0, vx1, vy1 = ux0, uy0, ux1, uy1
    elif rot == 90:
        # 90 deg CW: visual_w = unrot_h, visual_h = unrot_w
        # vx = H - uy, vy = ux
        vx0 = unrot_height - uy1
        vy0 = ux0
        vx1 = unrot_height - uy0
        vy1 = ux1
    elif rot == 180:
        # 180 deg CW:
        vx0 = unrot_width - ux1
        vy0 = unrot_height - uy1
        vx1 = unrot_width - ux0
        vy1 = unrot_height - uy0
    elif rot == 270:
        # 270 deg CW:
        vx0 = uy0
        vy0 = unrot_width - ux1
        vx1 = uy1
        vy1 = unrot_width - ux0
    else:
        raise ValueError(f"Unsupported rotation angle: {rotation_deg}. Must be 0, 90, 180, or 270.")

    min_x, max_x = min(vx0, vx1), max(vx0, vx1)
    min_y, max_y = min(vy0, vy1), max(vy0, vy1)
    return VisualRect(min_x, min_y, max_x, max_y)


def clamp_and_pad_rect(
    rect: VisualRect,
    max_width: float,
    max_height: float,
    padding: float = 1.5,
) -> VisualRect:
    """Add safety padding in points and clamp strictly to page visual boundary."""
    # Guard against completely out-of-bounds rects
    clamped_x0 = max(0.0, min(rect.x0 - padding, max_width))
    clamped_y0 = max(0.0, min(rect.y0 - padding, max_height))
    clamped_x1 = max(clamped_x0, min(rect.x1 + padding, max_width))
    clamped_y1 = max(clamped_y0, min(rect.y1 + padding, max_height))

    # If collapsed at border, ensure minimal non-negative span
    return VisualRect(x0=clamped_x0, y0=clamped_y0, x1=clamped_x1, y1=clamped_y1)
