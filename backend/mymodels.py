from sqlalchemy.ext.declarative import declarative_base, Column
from datetime import date, datetime
import ConfigParser
from lib.TVRage import TVRage

Base = declarative_base()

class Show(Base):
    __tablename__ = 'show'
    id = Column(Base.Integer, primary_key=True)
    name = Column(Base.String(128), unique=True)
    show_link = Column(Base.String(255))
    show_id = Column(Base.Integer(16), unique=True)
    origin_country = Column(Base.String(8), nullable=True)
    started = Column(Base.String(32), nullable=True)
    ended = Column(Base.String(32), nullable=True)
    status = Column(Base.String(32), nullable=True)
    runtime = Column(Base.Integer(8), nullable=True)
    total_seasons = Column(Base.Integer(8), nullable=True)
    airtime = Column(Base.String(32), nullable=True)
    air_day = Column(Base.String(32), nullable=True)
    classification = Column(Base.String(32), nullable=True)
    image = Column(Base.String(255), nullable=True)
    episodes = Base.relationship('Episode', backref='show')

    def __init__(self, name, *args, **kwargs):
        super(Show, self).__init__(*args, **kwargs)
        self.name = name

    def to_string(self):
        """
        :return: A string representation of the model.
        :rtype: string
        """
        string = ""
        for attr, value in self.__dict__.iteritems():
            string += str(attr) + ": " + str(value) + "\n"
        return string

    def update(self, connector):
        """
        Update object with data retrieved by connector.

        :param connector: Fetches show data from sources.
        :type connector: TVRage
        """
        show_data = connector.update(self.name)
        self.show_link = show_data['showlink']
        self.show_id = show_data['showid']
        self.origin_country = show_data['origin_country']
        self.started = show_data['started']
        self.ended = show_data['ended']
        self.status =show_data['status']
        self.runtime = show_data['runtime']
        self.total_seasons = show_data['totalseasons']
        self.airtime = show_data['airhours']
        self.air_day = show_data['airday']
        self.classification = show_data['classification']
        self.image = show_data['image']
        self.save()

    def update_with_episodes(self, connector):
        """
        Wraps show and episode updates.

        :param connector: TVRage
        """
        self.update(connector)
        self.update_episodes(connector)

    def update_episodes(self, connector):
        """
        Update episodes for show.

        :param connector: TVRage
        """
        episode_data = connector.update_episodes(self.show_id)
        for ep in episode_data:
            episode = Episode()
            episode.show = self
            for query_item, value in episode.__dict__.iteritems():
                if query_item in ep:
                    setattr(episode, query_item, ep[query_item])
            episode.save()

    def get_next_episode(self):
        """
        Find next not yet aired episode for show.

        :return: Episode or None
        """
        next = None
        for item in self.episodes:
            if item.airdate > date.today():
                if next == None:
                    next = item
                    continue
                elif next.airdate > item.airdate:
                    next = item
        return next

    def get_last_episode(self):
        next = None
        for item in self.episodes:
            if item.airdate < date.today():
                if next == None:
                    next = item
                    continue
                elif next.airdate < item.airdate:
                    next = item
        return next

    def get_last_episode_search_item(self):
        last_episode = self.get_last_episode()
        search_item = ''
        search_item += unicode(self.name) + ' '
        search_item += 'S' + unicode('%02d' % last_episode.seasonnum)
        search_item += 'E' + unicode('%02d' % last_episode.epnum)
        return search_item



class Episode(Base):
    __tablename__ = 'episode'
    id = Column(Base.Integer, primary_key=True)
    num = Column(Base.Integer(4), blank=True, null=True)
    ep_num = Column(Base.Integer(2), blank=True, null=True)
    season_num = Column(Base.Integer(2), blank=True, null=True)
    air_date = Column(blank=True, null=True)
    link = Column(Base.String(255), null=True)
    title = Column(Base.String(1024), blank=True, null=True)
    screen_cap = Column(Base.String(255), null=True)
    show = Column(Base.Integer, Base.ForeignKey('show.id'))

    def to_string(self):
        string = ""
        for attr, value in self.__dict__.iteritems():
            string += unicode(attr) + ": " + unicode(value) + u'\n'
        return string


class Subscription(Model):
    __tablename__ = 'subscription'
    id = Column(Integer, primary_key=True)
    show = Column(Integer, ForeignKey('show.id'))
    last_downloaded_episode_id = Column(Integer, ForeignKey('episode.id'))
    next_pull_date = DateField()

    def get_subscriptions(self):
        config = ConfigParser.ConfigParser()
        config.read('./subscriptions.cfg')
        return config.sections()


class Schedule:
    schedule_data = []

    def set_schedule(self):
        connector = TVRage()
        self.schedule_data = connector.current_schedule()

    def get_schedule_for_day(self, date):
        pass

