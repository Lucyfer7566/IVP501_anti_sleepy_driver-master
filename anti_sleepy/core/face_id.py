import math
import cv2
import numpy as np
from typing import List, Tuple, Optional

def euclidean_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

def extract_face_signature(landmarks: List[Tuple[int, int]]) -> List[float]:
    """
    Extracts a normalized signature of stable facial landmarks.
    """
    if not landmarks:
        return []

    NORM_P1, NORM_P2 = 226, 446
    PAIRS = [
        (10, 152), (234, 454), (70, 300), (1, 4), (57, 287),
        (33, 263), (168, 1), (10, 1), (152, 1), (234, 1),
        (454, 1), (57, 1), (287, 1), (70, 1), (300, 1)
    ]
    
    req_indices = set()
    for (a, b) in PAIRS:
        req_indices.add(a)
        req_indices.add(b)
    req_indices.add(NORM_P1)
    req_indices.add(NORM_P2)
    max_idx = max(req_indices)
    
    if len(landmarks) <= max_idx:
        return []
        
    norm_dist = euclidean_distance(landmarks[NORM_P1], landmarks[NORM_P2])
    if norm_dist <= 1e-6:
        return [0.0] * len(PAIRS)
        
    sig = []
    for (i, j) in PAIRS:
        dist = euclidean_distance(landmarks[i], landmarks[j])
        sig.append(dist / norm_dist)
    return sig

def average_signatures(sigs: List[List[float]]) -> List[float]:
    if not sigs:
        return []
    n = len(sigs)
    length = len(sigs[0])
    avg = [0.0] * length
    for sig in sigs:
        for i in range(min(length, len(sig))):
            avg[i] += sig[i]
    return [x / n for x in avg]

def compare_signatures(sig1: List[float], sig2: List[float]) -> float:
    """L2-based similarity between two face signatures."""
    if not sig1 or not sig2 or len(sig1) != len(sig2):
        return 0.0
    sq_sum = sum((a - b) ** 2 for a, b in zip(sig1, sig2))
    l2_dist = math.sqrt(sq_sum)
    return 1.0 / (1.0 + l2_dist)

# ============================================================
# Histogram-based face comparison (robust to head pose)
# ============================================================

def extract_face_crop(frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
    """
    Crop and normalize the face region to a standard size grayscale image.
    """
    x1, y1, x2, y2 = bbox
    if x2 <= x1 or y2 <= y1:
        return None
    
    face_crop = frame[y1:y2, x1:x2]
    if face_crop.size == 0:
        return None
    
    # Convert to grayscale
    if len(face_crop.shape) == 3:
        face_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    
    # Resize to standard size for consistent comparison
    face_crop = cv2.resize(face_crop, (128, 128))
    
    # Apply histogram equalization for lighting normalization
    face_crop = cv2.equalizeHist(face_crop)
    
    return face_crop

def compute_face_histogram(face_crop: np.ndarray) -> np.ndarray:
    """
    Compute a normalized histogram descriptor for a face crop.
    Uses spatial histogram (divide face into grid cells) for better discrimination.
    """
    if face_crop is None:
        return np.array([])
    
    # Divide face into 4x4 grid for spatial awareness
    h, w = face_crop.shape[:2]
    cell_h, cell_w = h // 4, w // 4
    
    histograms = []
    for row in range(4):
        for col in range(4):
            cell = face_crop[row*cell_h:(row+1)*cell_h, col*cell_w:(col+1)*cell_w]
            hist = cv2.calcHist([cell], [0], None, [32], [0, 256])
            cv2.normalize(hist, hist)
            histograms.append(hist.flatten())
    
    return np.concatenate(histograms)

def compare_face_histograms(hist1: np.ndarray, hist2: np.ndarray) -> float:
    """
    Compare two spatial face histograms using correlation.
    Returns similarity from -1 to 1 (1 = identical).
    """
    if hist1.size == 0 or hist2.size == 0 or hist1.shape != hist2.shape:
        return 0.0
    
    return cv2.compareHist(
        hist1.astype(np.float32).reshape(-1, 1),
        hist2.astype(np.float32).reshape(-1, 1),
        cv2.HISTCMP_CORREL
    )

def save_face_descriptor(frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
    """
    Extract and return the histogram descriptor for saving in the profile.
    """
    crop = extract_face_crop(frame, bbox)
    if crop is None:
        return None
    return compute_face_histogram(crop)

def is_owner(
    current_sig: List[float], 
    saved_sig: List[float],
    current_hist: Optional[np.ndarray] = None,
    saved_hist: Optional[np.ndarray] = None,
    yaw: float = 0.0,
    sig_threshold: float = 0.70,
    hist_threshold: float = 0.55
) -> Tuple[bool, float]:
    """
    Determine if the current face matches the saved owner.
    
    Uses a dual approach:
    1. Landmark signature (L2 similarity) - good when facing forward
    2. Histogram comparison - more robust to head rotation
    
    When head is turned (|yaw| > 25 degrees), relies more on histogram.
    
    Returns (is_match, combined_score).
    """
    sig_sim = compare_signatures(current_sig, saved_sig)
    
    hist_sim = 0.0
    has_hist = current_hist is not None and saved_hist is not None
    if has_hist:
        hist_sim = compare_face_histograms(current_hist, saved_hist)
        hist_sim = max(0.0, hist_sim)  # Clamp negatives
    
    abs_yaw = abs(yaw)
    
    if has_hist:
        # Blend: when facing forward, weight signature more; when turned, weight histogram more
        if abs_yaw < 15:
            # Front facing: 60% signature, 40% histogram
            combined = sig_sim * 0.6 + hist_sim * 0.4
            threshold = 0.55
        elif abs_yaw < 30:
            # Slight turn: 30% signature, 70% histogram
            combined = sig_sim * 0.3 + hist_sim * 0.7
            threshold = 0.50
        else:
            # Strong turn: rely almost entirely on histogram
            combined = sig_sim * 0.1 + hist_sim * 0.9
            threshold = 0.45
    else:
        # No histogram available, use signature only
        combined = sig_sim
        threshold = sig_threshold
    
    return combined >= threshold, combined
