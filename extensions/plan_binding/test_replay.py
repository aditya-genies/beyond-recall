"""Focused SQLite controls for the posthoc integration; no model calls."""
from pathlib import Path
import tempfile
import unittest
import replay


class AddressControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"effects.sqlite"
        replay.initialize(self.path,[])
        self.first=dict(kind="put",target=None,key="style",value="concise")
        self.address=replay.apply(self.path,self.first,"control",0,"prefix","replan_positional","case",exposed_new_id="control-first-effect")

    def test_same_key_literal_value_change_is_not_structural_alias(self):
        changed=dict(kind="put",target=None,key="style",value="brief")
        replay.apply(self.path,changed,"control",0,"recovery","replan_positional","case")
        result=replay.observe(self.path,self.address,self.first)
        self.assertFalse(result["structural_alias"])
        self.assertTrue(result["prefix_binding_preserved"])
        self.assertFalse(result["literal_prefix_record_preserved"])

    def test_fresh_address_cross_key_put_preserves_completed_prefix(self):
        changed=dict(kind="put",target=None,key="units",value="metric")
        replay.apply(self.path,changed,"control",0,"recovery","replan_fresh","case")
        result=replay.observe(self.path,self.address,self.first)
        self.assertFalse(result["structural_alias"])
        self.assertTrue(result["prefix_binding_preserved"])
        self.assertEqual(len(result["final_records"]),2)

    def test_mismatched_partial_public_id_is_rejected(self):
        expected=[dict(id="unrelated-id",key="style",value="concise")]
        with self.assertRaisesRegex(ValueError,"archived partial snapshot"):
            replay.require_partial(self.path,expected)


if __name__=="__main__":
    unittest.main()
