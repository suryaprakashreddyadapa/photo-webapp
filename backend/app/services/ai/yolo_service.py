"""
YOLO object detection service for automatic tagging.
"""
import numpy as np
from PIL import Image
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import structlog
from ultralytics import YOLO

from app.core.config import settings


logger = structlog.get_logger()

# Global model instance
_model = None


@dataclass
class Detection:
    """Object detection result."""
    class_name: str
    confidence: float
    x: float  # Normalized 0-1
    y: float
    width: float
    height: float


# COCO class names
COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
    'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
    'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
    'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
    'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
    'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
    'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
    'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
    'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
    'toothbrush'
]


def load_yolo_model() -> YOLO:
    """Load the YOLO model."""
    global _model
    
    if _model is not None:
        return _model
    
    logger.info(f"Loading YOLO model: {settings.YOLO_MODEL}")
    
    _model = YOLO(settings.YOLO_MODEL)
    
    logger.info("YOLO model loaded successfully")
    
    return _model


def detect_objects(
    image_path: str,
    confidence_threshold: float = 0.25,
    max_detections: int = 100
) -> List[Detection]:
    """Detect objects in an image using YOLO."""
    try:
        model = load_yolo_model()
        
        # Run inference
        results = model(image_path, verbose=False, conf=confidence_threshold)
        
        if not results or len(results) == 0:
            return []
        
        result = results[0]
        
        # Get image dimensions
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        detections = []
        boxes = result.boxes
        
        if boxes is None or len(boxes) == 0:
            return []
        
        for i in range(min(len(boxes), max_detections)):
            box = boxes[i]
            
            # Get class and confidence
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            
            if class_id >= len(COCO_CLASSES):
                continue
            
            class_name = COCO_CLASSES[class_id]
            
            # Get bounding box (xyxy format)
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            
            # Normalize coordinates
            detection = Detection(
                class_name=class_name,
                confidence=confidence,
                x=x1 / img_width,
                y=y1 / img_height,
                width=(x2 - x1) / img_width,
                height=(y2 - y1) / img_height
            )
            detections.append(detection)
        
        logger.debug(f"Detected {len(detections)} objects in {image_path}")
        return detections
        
    except Exception as e:
        logger.error(f"Error detecting objects in {image_path}: {e}")
        return []


def detect_objects_from_pil(
    image: Image.Image,
    confidence_threshold: float = 0.25,
    max_detections: int = 100
) -> List[Detection]:
    """Detect objects from a PIL Image."""
    try:
        model = load_yolo_model()
        
        # Convert PIL to numpy
        img_array = np.array(image.convert("RGB"))
        img_width, img_height = image.size
        
        # Run inference
        results = model(img_array, verbose=False, conf=confidence_threshold)
        
        if not results or len(results) == 0:
            return []
        
        result = results[0]
        detections = []
        boxes = result.boxes
        
        if boxes is None or len(boxes) == 0:
            return []
        
        for i in range(min(len(boxes), max_detections)):
            box = boxes[i]
            
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            
            if class_id >= len(COCO_CLASSES):
                continue
            
            class_name = COCO_CLASSES[class_id]
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            
            detection = Detection(
                class_name=class_name,
                confidence=confidence,
                x=x1 / img_width,
                y=y1 / img_height,
                width=(x2 - x1) / img_width,
                height=(y2 - y1) / img_height
            )
            detections.append(detection)
        
        return detections
        
    except Exception as e:
        logger.error(f"Error detecting objects from PIL image: {e}")
        return []


def get_unique_tags(detections: List[Detection]) -> List[Tuple[str, float]]:
    """Get unique object tags with highest confidence from detections."""
    tag_confidences = {}
    
    for detection in detections:
        tag = detection.class_name
        if tag not in tag_confidences or detection.confidence > tag_confidences[tag]:
            tag_confidences[tag] = detection.confidence
    
    # Sort by confidence
    sorted_tags = sorted(tag_confidences.items(), key=lambda x: x[1], reverse=True)
    return sorted_tags


def batch_detect_objects(
    image_paths: List[str],
    confidence_threshold: float = 0.25
) -> Dict[str, List[Detection]]:
    """Detect objects in multiple images."""
    results = {}
    
    for path in image_paths:
        detections = detect_objects(path, confidence_threshold)
        results[path] = detections
    
    return results


def get_scene_tags(detections: List[Detection]) -> List[str]:
    """Infer scene tags based on detected objects."""
    tags = set()
    object_names = [d.class_name for d in detections]
    
    # Indoor/outdoor inference
    outdoor_objects = {'car', 'truck', 'bus', 'bicycle', 'motorcycle', 'traffic light', 
                       'stop sign', 'bird', 'dog', 'cat', 'horse', 'cow', 'sheep',
                       'elephant', 'bear', 'zebra', 'giraffe', 'airplane', 'boat'}
    indoor_objects = {'couch', 'bed', 'dining table', 'toilet', 'tv', 'laptop',
                      'microwave', 'oven', 'refrigerator', 'sink'}
    
    outdoor_count = sum(1 for obj in object_names if obj in outdoor_objects)
    indoor_count = sum(1 for obj in object_names if obj in indoor_objects)
    
    if outdoor_count > indoor_count:
        tags.add('outdoor')
    elif indoor_count > outdoor_count:
        tags.add('indoor')
    
    # Activity inference
    if 'sports ball' in object_names or 'tennis racket' in object_names:
        tags.add('sports')
    
    if 'cake' in object_names or 'wine glass' in object_names:
        tags.add('celebration')
    
    food_objects = {'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot',
                    'hot dog', 'pizza', 'donut', 'cake'}
    if any(obj in food_objects for obj in object_names):
        tags.add('food')
    
    # Animal inference
    animals = {'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 
               'bear', 'zebra', 'giraffe', 'teddy bear'}
    if any(obj in animals for obj in object_names):
        tags.add('animals')
    
    # Vehicle inference
    vehicles = {'car', 'truck', 'bus', 'motorcycle', 'bicycle', 'airplane', 'boat', 'train'}
    if any(obj in vehicles for obj in object_names):
        tags.add('vehicles')
    
    # People
    if 'person' in object_names:
        person_count = object_names.count('person')
        if person_count == 1:
            tags.add('portrait')
        elif person_count > 3:
            tags.add('group')
    
    return list(tags)
