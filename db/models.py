from sqlalchemy.ext.declarative import declarative_base
from datetime import date, datetime
import ConfigParser
from lib.TVRage import TVRage

Base = declarative_base()

class Show(Base):
    __tablename__ = 'show'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True)
    showlink = Column(String(255))
    showid = Column(Integer(16), unique=True)
    origin_country = Column(String(8), nullable=True)
    started = Column(String(32), nullable=True)
    ended = Column(String(32), nullable=True)
    status = Column(String(32), nullable=True)
    runtime = Column(Integer(8), nullable=True)
    totalseasons = Column(Integer(8), nullable=True)
    airtime = Column(String(32), nullable=True)
    airday = Column(String(32), nullable=True)
    classification = Column(String(32), nullable=True)
    image = Column(String(255), nullable=True)
    episodes = relationship('Episode', backref='show')

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
        self.name = CharField(max_length=128, unique=True)
        self.showlink = show_data['showlink']
        self.showid = show_data['showid']
        self.origin_country = show_data['origin_country']
        self.started = show_data['started']
        self.ended = show_data['ended']
        self.status =show_data['status']
        self.runtime = show_data['runtime']
        self.totalseasons = show_data['totalseasons']
        self.airtime = show_data['airhours']
        self.airday = show_data['airday']
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
        episode_data = connector.update_episodes(self.showid)
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



class Episode(Model):
    __tablename__ = 'episode'
    id = Column(Integer, primary_key=True)
    num = IntegerField(Integer(4), blank=True, null=True)
    epnum = IntegerField(Integer(2), blank=True, null=True)
    seasonnum = IntegerField(Integer(2), blank=True, null=True)
    airdate = DateField(blank=True, null=True)
    link = URLField(String(255), null=True)
    title = CharField(String(1024), blank=True, null=True)
    screencap = URLField(String(255), null=True)
    show = Column(Integer, ForeignKey('show.id'))

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

