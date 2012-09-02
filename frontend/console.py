from backend.entity import Show, Episode, Subscription, EntityManager, Base, Session
import ConfigParser
from datetime import datetime, tzinfo

class SubscriptionAdapter(object):
    subscription_file = 'subscriptions.cfg'

    def __init__(self, entity_manager):
        self.entity_manager = entity_manager

    def generate_subscription_file_template(self):
        subscriptions = ConfigParser.RawConfigParser()
        session = Session()
        query = session.query(Show).all()
        for show in query:
            last_episode = show.get_last_episode()
            subscriptions.add_section(show.name)
            subscriptions.set(show.name, 'id', show.id)
            subscriptions.set(show.name, 'subscribed', 'false')
            subscriptions.set(show.name, 'season', last_episode.season_num)
            subscriptions.set(show.name, 'episode', last_episode.ep_num)
            subscriptions.set(show.name, 'last', last_episode.air_date)

        with open(self.subscription_file, 'wb') as file:
            subscriptions.write(file)

    def load_subscriptions_from_file(self):
        subscriptions = ConfigParser.RawConfigParser()
        try:
            subscriptions.readfp(open(self.subscription_file))
        except IOError:
            raise IOError
        for show_name in subscriptions.sections():
            pass



class SubscriptionManager(object):
    pass


if __name__ == '__main__':
    entity_manager = EntityManager(Base)
    entity_manager.connect_db()
    sca = SubscriptionAdapter(entity_manager)
    #sca.generate_subscription_file_template()
    sca.load_subscriptions_from_file()
