import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from urls import canonicalize, in_scope

class UrlTests(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(canonicalize('HTTPS://WWW.KENNESAW.EDU:443/a/../b/%7e?q=%2f#x'),
                         'https://www.kennesaw.edu/b/~?q=%2F')
    def test_relative(self):
        self.assertEqual(canonicalize('../x', 'https://www.kennesaw.edu/a/b/'), 'https://www.kennesaw.edu/a/x')
    def test_slashes_and_dots(self):
        self.assertEqual(canonicalize('https://kennesaw.edu/a//b/.'), 'https://kennesaw.edu/a//b/')
        self.assertEqual(canonicalize('https://kennesaw.edu/a/%2e%2e/'), 'https://kennesaw.edu/')
    def test_scope(self):
        self.assertTrue(in_scope('https://ccse.kennesaw.edu/'))
        self.assertFalse(in_scope('https://kennesaw.edu.example.com/'))

if __name__ == '__main__':
    unittest.main()
