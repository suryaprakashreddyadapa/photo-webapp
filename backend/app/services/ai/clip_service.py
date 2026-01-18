"""
CLIP service for generating image and text embeddings for semantic search.
"""
import torch
import numpy as np
from PIL import Image
from typing import List, Optional, Tuple
import open_clip
import structlog
from functools import lru_cache

from app.core.config import settings


logger = structlog.get_logger()

# Global model instances
_model = None
_preprocess = None
_tokenizer = None
_device = None


def get_device():
    """Get the best available device."""
    global _device
    if _device is None:
        if torch.cuda.is_available():
            _device = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            _device = torch.device("mps")
        else:
            _device = torch.device("cpu")
        logger.info(f"CLIP using device: {_device}")
    return _device


def load_clip_model():
    """Load the CLIP model."""
    global _model, _preprocess, _tokenizer
    
    if _model is not None:
        return _model, _preprocess, _tokenizer
    
    logger.info(f"Loading CLIP model: {settings.CLIP_MODEL}")
    
    device = get_device()
    
    _model, _, _preprocess = open_clip.create_model_and_transforms(
        settings.CLIP_MODEL,
        pretrained=settings.CLIP_PRETRAINED,
        device=device
    )
    _tokenizer = open_clip.get_tokenizer(settings.CLIP_MODEL)
    
    _model.eval()
    
    logger.info("CLIP model loaded successfully")
    
    return _model, _preprocess, _tokenizer


def get_image_embedding(image_path: str) -> Optional[np.ndarray]:
    """Generate CLIP embedding for an image."""
    try:
        model, preprocess, _ = load_clip_model()
        device = get_device()
        
        image = Image.open(image_path).convert("RGB")
        image_tensor = preprocess(image).unsqueeze(0).to(device)
        
        with torch.no_grad():
            image_features = model.encode_image(image_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        embedding = image_features.cpu().numpy().flatten()
        
        # Ensure correct dimension
        if len(embedding) != settings.VECTOR_DIMENSION:
            logger.warning(f"CLIP embedding dimension mismatch: {len(embedding)} vs {settings.VECTOR_DIMENSION}")
            # Pad or truncate if necessary
            if len(embedding) < settings.VECTOR_DIMENSION:
                embedding = np.pad(embedding, (0, settings.VECTOR_DIMENSION - len(embedding)))
            else:
                embedding = embedding[:settings.VECTOR_DIMENSION]
        
        return embedding
        
    except Exception as e:
        logger.error(f"Error generating image embedding: {e}")
        return None


def get_image_embedding_from_pil(image: Image.Image) -> Optional[np.ndarray]:
    """Generate CLIP embedding from a PIL Image."""
    try:
        model, preprocess, _ = load_clip_model()
        device = get_device()
        
        image = image.convert("RGB")
        image_tensor = preprocess(image).unsqueeze(0).to(device)
        
        with torch.no_grad():
            image_features = model.encode_image(image_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        embedding = image_features.cpu().numpy().flatten()
        
        if len(embedding) != settings.VECTOR_DIMENSION:
            if len(embedding) < settings.VECTOR_DIMENSION:
                embedding = np.pad(embedding, (0, settings.VECTOR_DIMENSION - len(embedding)))
            else:
                embedding = embedding[:settings.VECTOR_DIMENSION]
        
        return embedding
        
    except Exception as e:
        logger.error(f"Error generating image embedding from PIL: {e}")
        return None


def get_text_embedding(text: str) -> Optional[np.ndarray]:
    """Generate CLIP embedding for text."""
    try:
        model, _, tokenizer = load_clip_model()
        device = get_device()
        
        text_tokens = tokenizer([text]).to(device)
        
        with torch.no_grad():
            text_features = model.encode_text(text_tokens)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        embedding = text_features.cpu().numpy().flatten()
        
        if len(embedding) != settings.VECTOR_DIMENSION:
            if len(embedding) < settings.VECTOR_DIMENSION:
                embedding = np.pad(embedding, (0, settings.VECTOR_DIMENSION - len(embedding)))
            else:
                embedding = embedding[:settings.VECTOR_DIMENSION]
        
        return embedding
        
    except Exception as e:
        logger.error(f"Error generating text embedding: {e}")
        return None


def get_batch_image_embeddings(image_paths: List[str]) -> List[Optional[np.ndarray]]:
    """Generate CLIP embeddings for a batch of images."""
    try:
        model, preprocess, _ = load_clip_model()
        device = get_device()
        
        images = []
        valid_indices = []
        
        for i, path in enumerate(image_paths):
            try:
                image = Image.open(path).convert("RGB")
                images.append(preprocess(image))
                valid_indices.append(i)
            except Exception as e:
                logger.warning(f"Failed to load image {path}: {e}")
        
        if not images:
            return [None] * len(image_paths)
        
        image_tensor = torch.stack(images).to(device)
        
        with torch.no_grad():
            image_features = model.encode_image(image_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        embeddings = image_features.cpu().numpy()
        
        # Map back to original indices
        result = [None] * len(image_paths)
        for idx, valid_idx in enumerate(valid_indices):
            emb = embeddings[idx]
            if len(emb) != settings.VECTOR_DIMENSION:
                if len(emb) < settings.VECTOR_DIMENSION:
                    emb = np.pad(emb, (0, settings.VECTOR_DIMENSION - len(emb)))
                else:
                    emb = emb[:settings.VECTOR_DIMENSION]
            result[valid_idx] = emb
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        return [None] * len(image_paths)


def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    return float(np.dot(embedding1, embedding2))


def find_similar_embeddings(
    query_embedding: np.ndarray,
    embeddings: List[np.ndarray],
    top_k: int = 10,
    threshold: float = 0.0
) -> List[Tuple[int, float]]:
    """Find the most similar embeddings to a query embedding."""
    if not embeddings:
        return []
    
    # Stack embeddings for batch computation
    embedding_matrix = np.stack(embeddings)
    
    # Compute similarities
    similarities = np.dot(embedding_matrix, query_embedding)
    
    # Get top-k indices
    if threshold > 0:
        valid_mask = similarities >= threshold
        valid_indices = np.where(valid_mask)[0]
        valid_similarities = similarities[valid_mask]
        
        sorted_indices = np.argsort(valid_similarities)[::-1][:top_k]
        return [(int(valid_indices[i]), float(valid_similarities[i])) for i in sorted_indices]
    else:
        sorted_indices = np.argsort(similarities)[::-1][:top_k]
        return [(int(i), float(similarities[i])) for i in sorted_indices]


# Pre-computed tag embeddings for common categories
COMMON_TAGS = [
    # Nature
    "beach", "mountain", "forest", "ocean", "sunset", "sunrise", "sky", "clouds",
    "snow", "rain", "flowers", "trees", "lake", "river", "waterfall",
    # Animals
    "dog", "cat", "bird", "horse", "fish", "butterfly", "wildlife",
    # People
    "portrait", "group photo", "selfie", "family", "friends", "baby", "child",
    # Activities
    "wedding", "birthday", "party", "vacation", "travel", "sports", "concert",
    "hiking", "swimming", "camping", "cooking", "reading",
    # Objects
    "food", "car", "building", "house", "street", "city", "architecture",
    # Scenes
    "indoor", "outdoor", "night", "day", "landscape", "cityscape",
]


@lru_cache(maxsize=1)
def get_tag_embeddings() -> dict:
    """Get pre-computed embeddings for common tags."""
    logger.info("Computing tag embeddings...")
    
    tag_embeddings = {}
    for tag in COMMON_TAGS:
        embedding = get_text_embedding(f"a photo of {tag}")
        if embedding is not None:
            tag_embeddings[tag] = embedding
    
    logger.info(f"Computed {len(tag_embeddings)} tag embeddings")
    return tag_embeddings


def auto_tag_image(image_path: str, threshold: float = 0.25, max_tags: int = 5) -> List[Tuple[str, float]]:
    """Automatically generate tags for an image using CLIP."""
    image_embedding = get_image_embedding(image_path)
    if image_embedding is None:
        return []
    
    tag_embeddings = get_tag_embeddings()
    
    tags_with_scores = []
    for tag, tag_embedding in tag_embeddings.items():
        similarity = compute_similarity(image_embedding, tag_embedding)
        if similarity >= threshold:
            tags_with_scores.append((tag, similarity))
    
    # Sort by similarity and return top tags
    tags_with_scores.sort(key=lambda x: x[1], reverse=True)
    return tags_with_scores[:max_tags]
