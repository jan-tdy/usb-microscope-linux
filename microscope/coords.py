"""Pure coordinate math between a displayed (possibly letterboxed, scaled)
pixmap and the original video frame it was built from — no Qt dependency,
so it's testable without a QApplication.
"""


def widget_to_frame(widget_x, widget_y, widget_w, widget_h, pixmap_w, pixmap_h, frame_w, frame_h):
    """A click at (widget_x, widget_y) inside the label -> (x, y) in frame
    pixel coordinates, or None if the click landed outside the image itself
    (the label is usually bigger than the centered pixmap it holds)."""
    if pixmap_w <= 0 or pixmap_h <= 0 or frame_w <= 0 or frame_h <= 0:
        return None
    offset_x = (widget_w - pixmap_w) / 2
    offset_y = (widget_h - pixmap_h) / 2
    x = widget_x - offset_x
    y = widget_y - offset_y
    if not (0 <= x < pixmap_w and 0 <= y < pixmap_h):
        return None
    return x * frame_w / pixmap_w, y * frame_h / pixmap_h


def frame_to_pixmap(frame_x, frame_y, pixmap_w, pixmap_h, frame_w, frame_h):
    """The inverse of widget_to_frame's scaling step, for drawing a stored
    frame-space point back onto the (possibly resized) displayed pixmap."""
    if frame_w <= 0 or frame_h <= 0:
        return None
    return frame_x * pixmap_w / frame_w, frame_y * pixmap_h / frame_h
