from lib import connector
from sqlalchemy import Integer, String, Column, DateTime, func
from sqlalchemy import *
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
Session = sessionmaker()

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
        return "<Show('%s, %s %s')>" % (self.name, self.air_day, self.airtime)

    def __init__(self, name, connector):
        self.name = name
        self.connector = connector

    def update(self):
        """
        Update object with data retrieved by connector.

        """
        show_data = self.connector.update_show(self.name)
        self.show_link = show_data['show_link']
        self.tvr_id = show_data['show_id']
        self.origin_country = show_data['origin_country']
        self.started = show_data['started']
        self.ended = show_data['ended']
        self.status =show_data['status']
        self.runtime = show_data['runtime']
        self.total_seasons = show_data['total_seasons']
        self.airtime = show_data['air_hours']
        self.air_day = show_data['air_day']
        self.classification = show_data['classification']
        self.image = show_data['image']

        return isinstance(self.tvr_id, int)

    def save(self):
        session = Session()
        session.add(self)
        session.commit()

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
    current_shows = []
    catalogue_connector = None

    def __init__(self, catalogue_connector):
        self.catalogue_connector = catalogue_connector

    def set_schedule(self):
        self.current_shows = self.catalogue_connector.current_shows()

    def get_schedule_for_day(self, date):
        pass

class EntityManager(object):
    """ Represents database interactions, is a singleton. """
    __single = None
    _base = None
    engine = None
    session = None
    database_engine = 'sqlite'
    database_path = '/data.sqlite'

    def __init__(self, declarative_base):
        self._base = declarative_base()

    def __new__(cls, *args, **kwargs):
        if cls != type(cls.__single):
            cls.__single = object.__new__(cls, *args, **kwargs)
        return cls.__single

    def init_db(self):
        if not self.engine:
            self._create_connection()
        self._base.metadata.create_all(self.engine)

    def _create_connection(self):
        engine_path = self.database_engine + '://' + self.database_path
        self.engine = create_engine(engine_path, echo=True)
        Session.configure(bind=self.engine)

    def update_shows(self):
        # get schedule
        schedule = Schedule(connector.EztvCatalogueConnector())
        try:
            schedule.set_schedule()
        except:
            raise IOError
        session = Session()
        print schedule.current_shows
        for show_name in schedule.current_shows:
            query = session.query(Show).filter_by(name=show_name).all()
            if not query: # found nothing in the db
                show = Show(show_name, connector.TvrageShowConnector())
            else:
                show = query.pop()
                show.connector = connector.TvrageShowConnector()
            if not show.tvr_id: # don't want stuff not in tv rage db
                continue
            else:
                session.add(show)
                print show.__repr__()
        session.commit()


if __name__ == '__main__':
    entity_manager = EntityManager(Base)
    entity_manager.init_db()
#    session = Session()
#    cc = connector.EztvCatalogueConnector()
#    sched = Schedule(cc)
#    sched.set_schedule()
#    q = session.query(Show).filter_by(name='Fringe').all()
#    if not q:
#        cs = connector.TvrageShowConnector()
#        show = Show('Fringe', cs)
#        show.update()
#        show.save()
#    else:
#        show = q.pop()
#    print show.__repr__()
    entity_manager.update_shows()







