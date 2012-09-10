import os
from datetime import datetime
from lib import connector
from sqlalchemy import Integer, String, Column, DateTime, func
from sqlalchemy import *
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Session = sessionmaker()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)

    def cancel_subscriptions(self):
        session = Session()
        query = session.query(Subscription, User).filter(
            User.id == Subscription.user_id).delete()

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
        return "<Show('%s (%s), %s %s')>" % (
            self.name, self.tvr_id, self.air_day, self.airtime)

    def __init__(self, name, connector):
        self.name = name
        self.connector = connector

    def get_last_episode(self):
        last_episode = None
        session = Session()
        all_episodes = session.query(Episode).filter(
            Episode.show_id == self.id).all()
        current_time = datetime.now()
        for episode in all_episodes:
            if episode.air_date and episode.air_date < current_time:
                last_episode = episode
        return last_episode

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
        self.status = show_data['status']
        self.runtime = show_data['runtime']
        self.total_seasons = show_data['total_seasons']
        self.airtime = show_data['air_hours']
        self.air_day = show_data['air_day']
        self.classification = show_data['classification']
        self.image = show_data['image']

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
        return "<Episode('%s, %02dx%02d')>" % (
            self.show_id, int(self.season_num), int(self.ep_num))

    def __init__(self, show_id, episode_data):
        self.show_id = show_id
        self.episode_data = episode_data
        self.num = int(self.episode_data['num'])

    def update(self):
        self.ep_num = int(self.episode_data['ep_num'])
        self.season_num = int(self.episode_data['season_num'])
        self.air_date = self.episode_data['air_date']
        self.link = self.episode_data['link']
        self.title = self.episode_data['title']
        self.screen_cap = self.episode_data['screen_cap']

    def save(self):
        session = Session()
        session.add(self)
        session.commit()


class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    show_id = Column(Integer, ForeignKey('shows.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    last_downloaded_episode_id = Column(Integer, ForeignKey('episodes.id'),
                                        nullable=True)
    active = Column(Boolean, nullable=False, default=True)


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
    module_root_dir = os.path.dirname(os.path.abspath(__file__))
    database_file = 'data.sqlite'

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

    def connect_db(self):
        if not self.engine:
            self._create_connection()

    def _create_connection(self):
        engine_path = self.database_engine + ':///' + os.path.join(
            self.module_root_dir, self.database_file)
        print engine_path
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
        for show_name in schedule.current_shows:
            query = session.query(Show).filter_by(name=show_name).all()
            if not query: # found nothing in the db
                show = Show(show_name, connector.TvrageShowConnector())
            else:
                show = query.pop()
                show.connector = connector.TvrageShowConnector()
            show.update()
            if not show.tvr_id: # don't want stuff not in tv rage db
                continue
            else:
                session.add(show)
        session.commit()

    def update_episodes(self, show):
        session = Session()
        episode_connector = connector.TvrageEpisodeConnector()
        episodes = episode_connector.update_episodes(show)
        for ep in episodes:
            # see if we already got the episode in database
            query = session.query(Episode).join(Show).filter(
                Show.id == show.id).filter(Episode.num == ep['num']).all()
            if not query:
                episode = Episode(show.id, ep)
            else:
                episode = query.pop()
                episode.episode_data = ep
                episode.connector = episode_connector
            episode.update()
            session.add(episode)
        session.commit()

    def create_console_user(self):
        return_value = None
        session = Session()
        if not session.query(User).filter(User.username == 'console'):
            console_user = User()
            console_user.username = 'console'
            session.add(console_user)
            session.commit()
            return_value = console_user
        return return_value


if __name__ == '__main__':
    entity_manager = EntityManager(Base)
    #entity_manager.connect_db()
    entity_manager.init_db()
    session = Session()
    entity_manager.update_shows()
    query = session.query(Show).all()
    for show in query:
        entity_manager.update_episodes(show)







