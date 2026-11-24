import tempfile
import unittest
from pathlib import Path

from catalog_snapshot_audit import compare, live_coverage

class CatalogAuditTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.tmp = Path(handle.name)

    def write(self, name, text):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_snapshots_distinguish_repeated_labels_from_additions(self):
        okr = self.write("okr.csv", "OKR Number,Other Names,Collection Number,Comments\nKH0001,AS1,,\nKH0002,,,\n")
        guide = self.write("guide.csv", "okr_name,kfg_name\nKH0001,A\nKH0001,B\nCM001,C\nKH0003,D\n")
        result = compare(okr, guide)
        self.assertEqual(result["counts"]["shared_KH_labels"], 1)
        self.assertEqual(result["counts"]["guide_non_KH_label_rows"], 1)
        self.assertEqual(result["guide_repeated_KH_labels_not_auto_merged"], {"KH0001":["A","B"]})
        self.assertEqual(result["guide_only_KH_labels_not_claimed_absent_in_okr"], ["KH0003"])

    def test_alias_candidates_do_not_join_blank_aliases(self):
        path = self.write("index.html", """<table class="sortable">
          <tr><th>Name</th><th>Aliases</th></tr>
          <tr><td><a>KH0001</a></td><td></td></tr>
          <tr><td><a>KH0001A</a></td><td></td></tr>
          <tr><td><a>KT007</a></td><td></td></tr>
          <tr><td><a>KT008</a></td><td>A S1</td></tr></table>""")
        rows = [{"OKR Number":"KH0001","Other Names":"AS1"}, {"OKR Number":"KH0002","Other Names":""}]
        result = live_coverage(path,rows)
        self.assertEqual(result["shared_exact_KH_labels"], 1)
        self.assertEqual(result["okr_labels_without_exact_display_label"], ["KH0002"])
        self.assertEqual([r["candidate_okr_labels"] for r in result["non_KH_display_rows"]],
                         [["KH0001"],[],["KH0001"]])

    def test_reject_duplicate_pinned_okr_key(self):
        okr = self.write("okr.csv", "OKR Number,Other Names\nKH0001,\nKH0001,\n")
        guide = self.write("guide.csv", "okr_name,kfg_name\nKH0001,A\n")
        with self.assertRaisesRegex(ValueError,"unique KH"):
            compare(okr, guide)

if __name__ == "__main__":
    unittest.main()
