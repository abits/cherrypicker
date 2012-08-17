from lib import connector
from sqlalchemy import Integer, String, Column, DateTime, func
from sqlalchemy import *
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()


class Show(Base):
    __tablename__ = 'shows'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    show_link = Column(String)
    tvr_id = Column(Integer, unique=True, index=True)
    origin_country = Column(String, nullable=True)
    started = Column(String, nullable=True)
    ended = Column(String, nullable=True)
    status = Column(String, nullable=True)
    runtime = Column(Integer, nullable=True)
    total_seasons = Column(Integer, nullable=True)
    airtime = Column(String, nullable=True)
    air_day = Column(String, nullable=True)
    classification = Column(String, nullable=True)
    image = Column(String, nullable=True)
    episodes = relationship('Episode', backref='show')
    updated_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return "<Show('%s')>" % (self.name)

    def __init__(self, name):
        self.name = name


class Episode(Base):
    __tablename__ = 'episodes'
    id = Column(Integer, primary_key=True)
    num = Column(Integer, nullable=True)
    ep_num = Column(Integer, nullable=True)
    season_num = Column(Integer, nullable=True)
    air_date = Column(DateTime, nullable=True)
    link = Column(String, nullable=True)
    title = Column(String, nullable=True)
    screen_cap = Column(String, nullable=True)
    show_id = Column(Integer, ForeignKey('shows.id'), nullable=False)

    def __repr__(self):
        return "<Episode('%s','%s', '%s')>" % (self.name, self.tvr_id, self.air_day)

    def __init__(self, show_id, season_num, ep_num):
        self.show_id = show_id
        self.season_num = season_num
        self.ep_num = ep_num


class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    show_id = Column(Integer, ForeignKey('shows.id'), nullable=True)
    last_downloaded_episode_id = Column(Integer, ForeignKey('episodes.id'), nullable=True)
    next_pull_date = Column(DateTime, nullable=True)

class Schedule(object):
    schedule_data = []
    catalogue_connector = None

    def __init__(self, catalogue_connector):
        self.catalogue_connector = catalogue_connector

    def set_schedule(self):
        self.schedule_data = self.catalogue_connector.current_shows()
        print self.schedule_data

    def get_schedule_for_day(self, date):
        pass

class EntityManager(object):
    def __init__(self, declarative_base):
        self.base = declarative_base()

    def update_db(self):
        engine = create_engine('sqlite:///data.db', echo=True)
        metadata = MetaData(engine)
        self.base.metadata.create_all(engine)

if __name__ == '__main__':
    entity_manager = EntityManager(Base)
    entity_manager.update_db()
    cc = connector.EztvConnector()
    sched = Schedule(cc)
    sched.set_schedule()
    sched.set_schedule()
