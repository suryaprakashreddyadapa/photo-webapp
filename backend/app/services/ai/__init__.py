"""
AI services for PhotoVault.
"""
from app.services.ai.clip_service import (
    get_image_embedding,
    get_text_embedding,
    get_batch_image_embeddings,
    auto_tag_image
)
from app.services.ai.face_service import (
    detect_faces,
    compare_faces,
    find_matching_person,
    cluster_faces
)
from app.services.ai.yolo_service import (
    detect_objects,
    get_unique_tags,
    get_scene_tags
)
from app.services.ai.search import (
    semantic_search,
    parse_natural_language_query
)

__all__ = [
    "get_image_embedding",
    "get_text_embedding",
    "get_batch_image_embeddings",
    "auto_tag_image",
    "detect_faces",
    "compare_faces",
    "find_matching_person",
    "cluster_faces",
    "detect_objects",
    "get_unique_tags",
    "get_scene_tags",
    "semantic_search",
    "parse_natural_language_query"
]
