from backend.entity import EntityManager, Show, Subscription, Episode, Base
import unittest
from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()


class TestEntityFunctions(unittest.TestCase):

    def setUp(self):
        self.base = declarative_base()
        self.em = EntityManager(Base)
        self.show_name = 'Blue Bloods'
        self.engine = create_engine('sqlite:///test.db', echo=True)

    def test_update_db(self):
        self.base.metadata.create_all(self.engine)

    def test_create_show(self):
        self.show = Show(self.show_name)
        self.assertIsInstance(self.show, Show)
        self.assertEqual(self.show_name, self.show.name)

if __name__ == '__main__':
    unittest.main()
