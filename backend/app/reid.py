"""
Person Re-Identification (Re-ID) module.

This module provides person re-identification capabilities to remember people
even after they leave and return to the camera view. It uses deep learning
embeddings to create a "fingerprint" for each person based on their appearance.

Features:
- Extract visual embeddings from person crops
- Match new detections with known persons
- Persistent person database
- Cosine similarity matching
"""

import os
import pickle
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
import numpy as np
import cv2

# We'll use a lightweight model that doesn't require torch
# For production, you can switch to torch-based OSNet
from app.config import settings


@dataclass
class PersonRecord:
    """Record of a known person."""
    person_id: str
    embedding: np.ndarray
    first_seen: float
    last_seen: float
    appearance_count: int = 1
    track_ids: List[int] = field(default_factory=list)
    thumbnail: Optional[np.ndarray] = None  # Small reference image
    
    def update_seen(self, track_id: int):
        """Update last seen time and track history."""
        self.last_seen = time.time()
        self.appearance_count += 1
        if track_id not in self.track_ids:
            self.track_ids.append(track_id)


class SimpleReID:
    """
    Lightweight Re-ID implementation using color histograms and HOG features.
    
    This is a simple but effective approach for controlled environments.
    For better accuracy, switch to deep learning models like OSNet.
    
    Features extracted:
    - Color histogram (HSV) - for clothing color
    - HOG (Histogram of Oriented Gradients) - for shape/posture
    - Aspect ratio - for height/build
    """
    
    def __init__(self, 
                 similarity_threshold: float = 0.65,
                 max_persons: int = 100,
                 db_path: str = "data/reid_db.pkl"):
        """
        Initialize Re-ID system.
        
        Args:
            similarity_threshold: Minimum similarity (0-1) to consider a match
            max_persons: Maximum number of persons to track
            db_path: Path to save/load person database
        """
        self.similarity_threshold = similarity_threshold
        self.max_persons = max_persons
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.persons: Dict[str, PersonRecord] = {}
        self.next_person_id = 1
        
        # Load existing database
        self._load_db()
        
        print(f"✓ Re-ID initialized: {len(self.persons)} known persons")
        print(f"  Similarity threshold: {similarity_threshold}")
        print(f"  Database: {self.db_path}")
    
    def extract_embedding(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Extract visual embedding from person crop.
        
        Args:
            frame: Full frame image
            bbox: Bounding box (x1, y1, x2, y2)
            
        Returns:
            Embedding vector (normalized numpy array)
        """
        x1, y1, x2, y2 = [int(v) for v in bbox]
        
        # Ensure valid crop
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return np.zeros(256)  # Invalid crop
        
        crop = frame[y1:y2, x1:x2]
        
        if crop.size == 0:
            return np.zeros(256)
        
        # Resize to standard size for consistency
        crop = cv2.resize(crop, (64, 128))
        
        # Extract features
        features = []
        
        # 1. Color histogram (HSV) - 48 dimensions
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [16], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [16], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], None, [16], [0, 256])
        
        features.append(hist_h.flatten())
        features.append(hist_s.flatten())
        features.append(hist_v.flatten())
        
        # 2. HOG features - simplified version
        # Convert to grayscale
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        
        # Compute gradients
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=1)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=1)
        
        # Gradient magnitude and direction
        mag, angle = cv2.cartToPolar(gx, gy, angleInDegrees=True)
        
        # Simple histogram of gradients - 9 bins
        bins = 9
        hist_grad = np.histogram(angle.flatten(), bins=bins, range=(0, 360), weights=mag.flatten())[0]
        features.append(hist_grad)
        
        # 3. Spatial color features - top/bottom color (for clothing)
        h_crop = crop.shape[0]
        top_third = crop[:h_crop//3, :]
        middle_third = crop[h_crop//3:2*h_crop//3, :]
        bottom_third = crop[2*h_crop//3:, :]
        
        for region in [top_third, middle_third, bottom_third]:
            if region.size > 0:
                mean_color = region.mean(axis=(0, 1))
                features.append(mean_color)
        
        # 4. Aspect ratio (height/width) - for body build
        aspect_ratio = crop.shape[0] / max(crop.shape[1], 1)
        features.append(np.array([aspect_ratio * 10]))  # Scale for better weight
        
        # Concatenate all features
        embedding = np.concatenate(features)
        
        # Normalize to unit length (for cosine similarity)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
    
    def find_match(self, embedding: np.ndarray, debug: bool = True) -> Optional[Tuple[str, float]]:
        """
        Find best matching person in database.
        
        Args:
            embedding: Query embedding
            debug: Print similarity scores for debugging
            
        Returns:
            Tuple of (person_id, similarity) if match found, None otherwise
        """
        if not self.persons or embedding is None:
            return None
        
        best_match = None
        best_similarity = 0.0
        all_similarities = []
        
        for person_id, person in self.persons.items():
            similarity = self.cosine_similarity(embedding, person.embedding)
            all_similarities.append((person_id, similarity))
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = person_id
        
        # Debug output - show all similarities
        if debug and all_similarities:
            print(f"  Re-ID similarities:")
            for pid, sim in sorted(all_similarities, key=lambda x: x[1], reverse=True):
                marker = "✓ MATCH" if sim >= self.similarity_threshold else "✗ below threshold"
                print(f"    {pid}: {sim:.3f} {marker}")
        
        # Only return match if above threshold
        if best_similarity >= self.similarity_threshold:
            return (best_match, best_similarity)
        
        return None
    
    def register_person(self, 
                       embedding: np.ndarray,
                       track_id: int,
                       thumbnail: Optional[np.ndarray] = None) -> str:
        """
        Register a new person in the database.
        
        Args:
            embedding: Person embedding
            track_id: Current track ID
            thumbnail: Small reference image (optional)
            
        Returns:
            New person_id
        """
        # Check if we've reached max persons
        if len(self.persons) >= self.max_persons:
            # Remove oldest person (by last_seen)
            oldest_id = min(self.persons.keys(), 
                          key=lambda k: self.persons[k].last_seen)
            del self.persons[oldest_id]
            print(f"⚠️  Re-ID DB full, removed oldest person: {oldest_id}")
        
        person_id = f"P{self.next_person_id:04d}"
        self.next_person_id += 1
        
        current_time = time.time()
        person = PersonRecord(
            person_id=person_id,
            embedding=embedding,
            first_seen=current_time,
            last_seen=current_time,
            track_ids=[track_id],
            thumbnail=thumbnail
        )
        
        self.persons[person_id] = person
        
        print(f"✨ New person registered: {person_id} (track_id={track_id})")
        
        # Save database
        self._save_db()
        
        return person_id
    
    def update_person(self, 
                     person_id: str,
                     track_id: int,
                     embedding: Optional[np.ndarray] = None):
        """
        Update person record with new appearance.
        
        Args:
            person_id: Person to update
            track_id: Current track ID
            embedding: New embedding (optional, for averaging)
        """
        if person_id not in self.persons:
            return
        
        person = self.persons[person_id]
        person.update_seen(track_id)
        
        # Optional: Update embedding with moving average for robustness
        if embedding is not None:
            alpha = 0.3  # Weight for new embedding
            person.embedding = (1 - alpha) * person.embedding + alpha * embedding
            
            # Re-normalize
            norm = np.linalg.norm(person.embedding)
            if norm > 0:
                person.embedding = person.embedding / norm
        
        # Periodically save database
        if person.appearance_count % 10 == 0:
            self._save_db()
    
    def get_person_info(self, person_id: str) -> Optional[Dict]:
        """Get information about a person."""
        if person_id not in self.persons:
            return None
        
        person = self.persons[person_id]
        return {
            "person_id": str(person_id),
            "first_seen": float(person.first_seen),
            "last_seen": float(person.last_seen),
            "appearance_count": int(person.appearance_count),
            "track_ids": [int(tid) for tid in person.track_ids],
            "has_thumbnail": person.thumbnail is not None
        }
    
    def get_all_persons(self) -> List[Dict]:
        """Get list of all known persons."""
        return [self.get_person_info(pid) for pid in self.persons.keys()]
    
    def clear_old_persons(self, max_age_days: int = 7):
        """Remove persons not seen in specified days."""
        current_time = time.time()
        max_age_seconds = max_age_days * 86400
        
        to_remove = []
        for person_id, person in self.persons.items():
            age = current_time - person.last_seen
            if age > max_age_seconds:
                to_remove.append(person_id)
        
        for person_id in to_remove:
            del self.persons[person_id]
        
        if to_remove:
            print(f"🧹 Removed {len(to_remove)} old persons")
            self._save_db()
        
        return len(to_remove)
    
    def reset_database(self):
        """Clear all persons from database."""
        self.persons.clear()
        self.next_person_id = 1
        self._save_db()
        print("🗑️  Re-ID database cleared")
    
    def _save_db(self):
        """Save person database to disk."""
        try:
            # Don't save thumbnails (too large)
            persons_to_save = {}
            for pid, person in self.persons.items():
                person_copy = PersonRecord(
                    person_id=person.person_id,
                    embedding=person.embedding,
                    first_seen=person.first_seen,
                    last_seen=person.last_seen,
                    appearance_count=person.appearance_count,
                    track_ids=person.track_ids,
                    thumbnail=None  # Don't save thumbnails
                )
                persons_to_save[pid] = person_copy
            
            with open(self.db_path, 'wb') as f:
                pickle.dump({
                    'persons': persons_to_save,
                    'next_person_id': self.next_person_id
                }, f)
        except Exception as e:
            print(f"⚠️  Failed to save Re-ID database: {e}")
    
    def _load_db(self):
        """Load person database from disk."""
        if not self.db_path.exists():
            return
        
        try:
            with open(self.db_path, 'rb') as f:
                data = pickle.load(f)
                self.persons = data.get('persons', {})
                self.next_person_id = data.get('next_person_id', 1)
            
            print(f"📂 Loaded Re-ID database: {len(self.persons)} persons")
        except Exception as e:
            print(f"⚠️  Failed to load Re-ID database: {e}")
            self.persons = {}
            self.next_person_id = 1


# Singleton instance
_reid_instance: Optional[SimpleReID] = None


def get_reid() -> SimpleReID:
    """Get global Re-ID instance (singleton)."""
    global _reid_instance
    if _reid_instance is None:
        _reid_instance = SimpleReID(
            similarity_threshold=settings.reid_similarity_threshold,
            max_persons=settings.reid_max_persons,
            db_path=settings.reid_db_path
        )
    return _reid_instance
