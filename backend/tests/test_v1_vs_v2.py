import unittest
import sys
from pathlib import Path

# Add backend to sys path
sys.path.append(str(Path(__file__).resolve().parent.parent))

class TestRegressionV1vsV2(unittest.TestCase):
    def test_v1_exists_and_isolated(self):
        # Phase 23: Ensure V1 is preserved
        v1_path = Path(__file__).resolve().parent.parent / "app" / "ml_v1"
        self.assertTrue(v1_path.exists(), "V1 directory was not preserved!")
        
        # Check if v2 exists
        v2_path = Path(__file__).resolve().parent.parent / "app" / "ml" / "v2"
        self.assertTrue(v2_path.exists(), "V2 directory missing!")

    def test_v2_evidence_fusion_logic(self):
        from app.ml.v2.evidence_fusion import EvidenceFusionEngine
        engine = EvidenceFusionEngine({"BALANCED_MODE": 0.65})
        
        # Test 1: OOD Check
        res_ood = engine.fuse(0.9, True, [], [])
        self.assertEqual(res_ood["final_classification"], "INCONCLUSIVE")
        self.assertTrue(res_ood["uncertainty"])
        
        # Test 2: Retouched Authentic overrides weak AI score
        res_retouched = engine.fuse(0.55, False, [], [{"type": "SKIN_SMOOTHING"}])
        self.assertEqual(res_retouched["final_classification"], "AUTHENTIC_DIGITALLY_RETOUCHED")
        
        # Test 3: Strong AI overrides
        res_ai = engine.fuse(0.85, False, [], [])
        self.assertEqual(res_ai["final_classification"], "AI_GENERATED")
        
if __name__ == "__main__":
    unittest.main()
