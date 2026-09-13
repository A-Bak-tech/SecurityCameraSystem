"""
Maps YOLOv5's raw COCO class names into the broader categories used
by SecurityCameraSystem's use cases (person / vehicle / animal / other).
"""

# COCO class names YOLOv5 can detect, grouped into our broader categories.
_VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle", "train"}
_ANIMAL_CLASSES = {
    "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe"
}


def classify_label(raw_label: str) -> str:
    """
    Converts a raw YOLOv5 class name (e.g. 'car', 'dog') into one of:
    'person', 'vehicle', 'animal', or 'other'.
    """
    if raw_label == "person":
        return "person"
    if raw_label in _VEHICLE_CLASSES:
        return "vehicle"
    if raw_label in _ANIMAL_CLASSES:
        return "animal"
    return "other"