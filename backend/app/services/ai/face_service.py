"""
Face recognition service using dlib/face_recognition library.
"""
import numpy as np
from PIL import Image
from typing import List, Optional, Tuple, Dict
import face_recognition
import structlog
from dataclasses import dataclass

from app.core.config import settings


logger = structlog.get_logger()


@dataclass
class DetectedFace:
    """Detected face with location and encoding."""
    x: float  # Normalized 0-1
    y: float
    width: float
    height: float
    encoding: np.ndarray
    confidence: float = 1.0


def detect_faces(image_path: str) -> List[DetectedFace]:
    """Detect faces in an image and return their locations and encodings."""
    try:
        # Load image
        image = face_recognition.load_image_file(image_path)
        height, width = image.shape[:2]
        
        # Detect face locations
        # Use CNN model for better accuracy if GPU available, otherwise HOG
        model = settings.FACE_RECOGNITION_MODEL
        face_locations = face_recognition.face_locations(image, model=model)
        
        if not face_locations:
            return []
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        faces = []
        for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
            # Normalize coordinates to 0-1 range
            face = DetectedFace(
                x=left / width,
                y=top / height,
                width=(right - left) / width,
                height=(bottom - top) / height,
                encoding=encoding
            )
            faces.append(face)
        
        logger.debug(f"Detected {len(faces)} faces in {image_path}")
        return faces
        
    except Exception as e:
        logger.error(f"Error detecting faces in {image_path}: {e}")
        return []


def detect_faces_from_pil(image: Image.Image) -> List[DetectedFace]:
    """Detect faces from a PIL Image."""
    try:
        # Convert PIL to numpy array
        image_array = np.array(image.convert("RGB"))
        height, width = image_array.shape[:2]
        
        model = settings.FACE_RECOGNITION_MODEL
        face_locations = face_recognition.face_locations(image_array, model=model)
        
        if not face_locations:
            return []
        
        face_encodings = face_recognition.face_encodings(image_array, face_locations)
        
        faces = []
        for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
            face = DetectedFace(
                x=left / width,
                y=top / height,
                width=(right - left) / width,
                height=(bottom - top) / height,
                encoding=encoding
            )
            faces.append(face)
        
        return faces
        
    except Exception as e:
        logger.error(f"Error detecting faces from PIL image: {e}")
        return []


def compare_faces(
    known_encoding: np.ndarray,
    unknown_encoding: np.ndarray,
    tolerance: float = None
) -> Tuple[bool, float]:
    """Compare two face encodings and return match status and distance."""
    if tolerance is None:
        tolerance = settings.FACE_RECOGNITION_TOLERANCE
    
    # Calculate Euclidean distance
    distance = np.linalg.norm(known_encoding - unknown_encoding)
    is_match = distance <= tolerance
    
    return is_match, float(distance)


def find_matching_person(
    face_encoding: np.ndarray,
    known_encodings: Dict[str, np.ndarray],
    tolerance: float = None
) -> Optional[Tuple[str, float]]:
    """Find the best matching person for a face encoding."""
    if tolerance is None:
        tolerance = settings.FACE_RECOGNITION_TOLERANCE
    
    if not known_encodings:
        return None
    
    best_match = None
    best_distance = float('inf')
    
    for person_id, known_encoding in known_encodings.items():
        is_match, distance = compare_faces(known_encoding, face_encoding, tolerance)
        if is_match and distance < best_distance:
            best_match = person_id
            best_distance = distance
    
    if best_match:
        return (best_match, best_distance)
    return None


def cluster_faces(
    face_encodings: List[np.ndarray],
    tolerance: float = None
) -> List[List[int]]:
    """Cluster face encodings into groups (potential persons)."""
    if tolerance is None:
        tolerance = settings.FACE_RECOGNITION_TOLERANCE
    
    if not face_encodings:
        return []
    
    n = len(face_encodings)
    assigned = [False] * n
    clusters = []
    
    for i in range(n):
        if assigned[i]:
            continue
        
        # Start new cluster
        cluster = [i]
        assigned[i] = True
        
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            
            is_match, _ = compare_faces(face_encodings[i], face_encodings[j], tolerance)
            if is_match:
                cluster.append(j)
                assigned[j] = True
        
        clusters.append(cluster)
    
    return clusters


def compute_average_encoding(encodings: List[np.ndarray]) -> np.ndarray:
    """Compute the average encoding for a person from multiple face encodings."""
    if not encodings:
        raise ValueError("No encodings provided")
    
    return np.mean(encodings, axis=0)


def get_face_crop(image_path: str, face: DetectedFace, padding: float = 0.2) -> Optional[Image.Image]:
    """Extract a cropped face image with padding."""
    try:
        image = Image.open(image_path)
        width, height = image.size
        
        # Calculate crop coordinates with padding
        x1 = max(0, int((face.x - padding * face.width) * width))
        y1 = max(0, int((face.y - padding * face.height) * height))
        x2 = min(width, int((face.x + face.width + padding * face.width) * width))
        y2 = min(height, int((face.y + face.height + padding * face.height) * height))
        
        cropped = image.crop((x1, y1, x2, y2))
        return cropped
        
    except Exception as e:
        logger.error(f"Error cropping face: {e}")
        return None


def estimate_face_quality(image_path: str, face: DetectedFace) -> float:
    """Estimate the quality of a detected face (0-1 score)."""
    try:
        face_crop = get_face_crop(image_path, face, padding=0.1)
        if face_crop is None:
            return 0.0
        
        # Convert to grayscale for blur detection
        gray = face_crop.convert("L")
        gray_array = np.array(gray)
        
        # Calculate Laplacian variance (blur detection)
        from scipy import ndimage
        laplacian = ndimage.laplace(gray_array.astype(float))
        blur_score = laplacian.var()
        
        # Normalize blur score (higher is better, less blurry)
        # Typical values range from 0 to 1000+
        blur_quality = min(1.0, blur_score / 500.0)
        
        # Face size quality (larger is better)
        face_area = face.width * face.height
        size_quality = min(1.0, face_area * 10)  # Normalize
        
        # Combined quality score
        quality = (blur_quality * 0.7 + size_quality * 0.3)
        
        return quality
        
    except Exception as e:
        logger.error(f"Error estimating face quality: {e}")
        return 0.5  # Default medium quality


def batch_detect_faces(image_paths: List[str]) -> Dict[str, List[DetectedFace]]:
    """Detect faces in multiple images."""
    results = {}
    
    for path in image_paths:
        faces = detect_faces(path)
        results[path] = faces
    
    return results
