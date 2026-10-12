"""Checks for analytical definitions with hand-calculated examples."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from analyze import shape, shingles, tokens

class AnalysisTests(unittest.TestCase):
    def test_shape_groups_query_values_but_not_names(self):
        self.assertEqual(shape('https://www.kennesaw.edu/items/123?page=1&sort=asc'),
                         shape('https://www.kennesaw.edu/items/456?sort=desc&page=999'))
        self.assertNotEqual(shape('https://www.kennesaw.edu/?page=1'),
                            shape('https://www.kennesaw.edu/?date=1'))

    def test_shingle_jaccard_hand_calculated(self):
        a=shingles('a b c d e f'.split())
        b=shingles('a b c d e g'.split())
        self.assertAlmostEqual(len(a&b)/len(a|b),1/3)
        self.assertEqual(shingles('a b c'.split()),set())

    def test_repeated_shingles_are_sets(self):
        self.assertEqual(len(shingles(['same']*12)),1)

    def test_tokenizer_policy(self):
        self.assertEqual(tokens("KSU's 2026 STUDENTS—Welcome!"),["ksu's",'students','welcome'])

if __name__=='__main__': unittest.main()
