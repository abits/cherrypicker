from backend.entity import Show, User, Subscription, EntityManager, Base, Session
import ConfigParser
from datetime import datetime, tzinfo

class FileError(Exception):
    pass

class SubscriptionFileError(FileError):
    """Exception raised for errors in the subscription file.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

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
        except IOError as e:
            print e
            raise IOError
        session = Session()
        for user in session.query(User).filter(User.username == 'console').all():
            user.cancel_subscriptions()
        for show in subscriptions.sections():
            self.update_from_file(session, subscriptions, show)
        session.commit()

    def update_from_file(self, session, config_file, item):
        if config_file.get(item, 'subscribed') == 'true':
            subscription = Subscription()
            subscription.active = True
            subscription.user_id = 1
            subscription.show_id = config_file.get(item, 'id')
            session.add(subscription)


class SubscriptionManager(object):
    pass


if __name__ == '__main__':
    entity_manager = EntityManager(Base)
    entity_manager.connect_db()
    user = entity_manager.create_console_user()
    sca = SubscriptionAdapter(entity_manager)
    #sca.generate_subscription_file_template()
    sca.load_subscriptions_from_file()

