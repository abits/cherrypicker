from lib.connector import TvrageShowConnector
from backend.entity import Show
import unittest


class TestConnectorFunctions(unittest.TestCase):

    def setUp(self):
        self.test_connector = TvrageShowConnector()

    def test_findShowId(self):
        self.assertEqual('25756', self.test_connector._findShowId('Blue Bloods'))
        self.assertEqual('4198', self.test_connector._findShowId('The David Letterman Show'))
        self.assertEqual('3332', self.test_connector._findShowId('Doctor Who'))
        self.assertEqual('31547', self.test_connector._findShowId('The Soul Man'))
        self.assertEqual('25652', self.test_connector._findShowId('Strike Back'))

if __name__ == '__main__':
    unittest.main()
