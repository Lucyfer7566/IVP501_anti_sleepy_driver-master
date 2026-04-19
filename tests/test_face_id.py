import pytest
import math
from anti_sleepy.core.face_id import (
    extract_face_signature,
    average_signatures,
    compare_signatures,
    is_owner,
    euclidean_distance
)

def test_extract_face_signature():
    # Provide exactly 468 mock landmarks (MediaPipe FaceMesh size)
    landmarks = [(i, i) for i in range(468)]
    
    sig = extract_face_signature(landmarks)
    assert len(sig) == 15
    
    # 226->446 dist: hypot(446-226, 446-226) = hypot(220, 220) = 220 * sqrt(2)
    # pair 1: 10->152 = hypot(142, 142) = 142 * sqrt(2)
    # expected normalized = 142 / 220 = 0.6454545
    assert math.isclose(sig[0], 142 / 220)

def test_extract_face_signature_invalid():
    assert extract_face_signature([]) == []
    assert extract_face_signature([(0,0), (1,1)]) == []

def test_average_signatures():
    sig1 = [1.0, 2.0, 3.0]
    sig2 = [3.0, 2.0, 1.0]
    sig3 = [2.0, 2.0, 2.0]
    
    avg = average_signatures([sig1, sig2, sig3])
    assert avg == [2.0, 2.0, 2.0]
    
    assert average_signatures([]) == []

def test_compare_signatures():
    sig1 = [1.0, 0.0]
    sig2 = [1.0, 0.0]
    # identical vectors -> Inverse L2 similarity 1.0
    assert math.isclose(compare_signatures(sig1, sig2), 1.0, rel_tol=1e-5)
    
    sig3 = [0.0, 1.0]
    # orthogonal vectors -> L2 dist = sqrt(2) -> similarity = 1/(1+sqrt(2)) ≈ 0.414
    sim = compare_signatures(sig1, sig3)
    expected = 1.0 / (1.0 + math.sqrt(2))
    assert math.isclose(sim, expected, rel_tol=1e-5)
    
    # Error cases
    assert compare_signatures([], []) == 0.0
    assert compare_signatures([0.0, 0.0], [0.0, 0.0]) == 1.0  # dist=0 -> 1/(1+0) = 1.0
    assert compare_signatures([1.0], [1.0, 2.0]) == 0.0

def test_is_owner():
    # Identical vectors -> high similarity -> is_owner True
    result, score = is_owner([1.0, 0.0], [1.0, 0.0], sig_threshold=0.92)
    assert result is True
    assert score >= 0.92
    # Orthogonal vectors -> low similarity -> is_owner False
    result2, score2 = is_owner([1.0, 0.0], [0.0, 1.0], sig_threshold=0.92)
    assert result2 is False

if __name__ == "__main__":
    test_extract_face_signature()
    test_extract_face_signature_invalid()
    test_average_signatures()
    test_compare_signatures()
    test_is_owner()
    print("SUCCESS: All tests passed!")
