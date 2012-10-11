from cherrypicker.entity import Show, User, Subscription, Session, Episode
from cherrypicker.entity import EntityManager, Base
from cherrypicker.connector import FilesTubeConnector
import cherrypicker
import ConfigParser
import logging
import pygtk
pygtk.require('2.0')
import gtk
import os
import sys
import argparse

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

class OptionFileError(FileError):
    """Exception raised for errors in the options file.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

class SubscriptionAdapter(object):
    subscription_file = os.path.join(cherrypicker.data_dir, 'subscriptions.cfg')

    def __init__(self, entity_manager):
        self.entity_manager = entity_manager

    def generate_subscription_file_template(self):
        subscriptions = ConfigParser.RawConfigParser()
        session = Session()
        query = session.query(Show).all()
        for show in query:
            try:
                last_episode = show.get_last_episode()
                subscriptions.add_section(show.name)
                subscriptions.set(show.name, 'id', show.id)
                subscriptions.set(show.name, 'subscribed', 'false')
                subscriptions.set(show.name, 'season', last_episode.season_num)
                subscriptions.set(show.name, 'episode', last_episode.ep_num)
                subscriptions.set(show.name, 'last', last_episode.air_date)

                with open(self.subscription_file, 'wb') as file:
                    subscriptions.write(file)
            except:
                pass

    def load_subscriptions_from_file(self):
        subscriptions = ConfigParser.RawConfigParser()
        try:
            subscriptions.readfp(open(self.subscription_file))
        except IOError as e:
            print e
            raise IOError
        session = Session()
        for user in session.query(User).\
        filter(User.username == 'console').all():
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

    def update_subscription_file(self,):
        subscriptions = ConfigParser.RawConfigParser()
        session = Session()
        query = session.query(Show).all()
        for show in query:
            subscribed = 'false'
            subscription_results = session.query(Subscription).\
                filter(Subscription.user_id == 1).\
                filter(Subscription.show_id == show.id).all()
            if subscription_results:
                subscribed = 'true'
            try:
                last_episode = show.get_last_episode()
                subscriptions.add_section(show.name)
                subscriptions.set(show.name, 'id', show.id)
                subscriptions.set(show.name, 'subscribed', subscribed)
                subscriptions.set(show.name, 'season', last_episode.season_num)
                subscriptions.set(show.name, 'episode', last_episode.ep_num)
                subscriptions.set(show.name, 'last', last_episode.air_date)

                with open(self.subscription_file, 'wb') as file:
                    subscriptions.write(file)
            except:
                pass



class SubscriptionManager(object):
    def __init__(self):
        self._option_manager = OptionsManager()

    def check_for_updates(self, username):
        session = Session()
        users = session.query(User).filter(User.username == username).all()
        user = users[0]  # username is unique
        subscriptions = session.query(Subscription).filter(
            Subscription.user_id == user.id)
        download_queue = []
        for subscription in subscriptions:
            shows = session.query(Show).filter(Show.id == subscription.show_id)
            current = shows[0].get_last_episode()
            if not isinstance(subscription.last_downloaded_episode_id,
                (int, long)):
                # we haven't downloaded any episode yet, so we simply fetch the
                # current one
                download_queue.append((subscription, current))
            else:
                # we already have downloaded episodes for this show, so we have
                # to check if we are up to date
                query = session.\
                query(Episode).\
                filter(Episode.id == subscription.last_downloaded_episode_id).\
                all()
                if not query:
                    # something went wrong
                    logging.error("console.py: Cannot find episode by id.")
                    continue
                else:
                    last_downloaded_episode = query[0]
                try:
                    index = last_downloaded_episode.get_next()
                    while index.air_date <= current.air_date:
                        download_queue.append((subscription, index))
                        index = index.get_next()
                except AttributeError:
                    logging.error("console.py: Something went wrong.")
        return download_queue

    def get_download_links(self, download_queue):
        download_items = {}
        for subscription, episode in download_queue:
            session = Session()
            shows = session.query(Show).\
                filter(Show.id == episode.show_id).all()
            search_string = '%s %sx%02d %s %s' % (
                                shows[0].name,
                                episode.season_num,
                                episode.ep_num,
                                ' '.join(self._option_manager.release_groups),
                                ' '.join(self._option_manager.quality))
            results = []
            for hoster in self._option_manager.hoster:
                client = FilesTubeConnector()
                client.update(search_string, host=hoster)
                for res in client.getResults():
                    res['episode_id'] = episode.id
                    res['subscription_id'] = subscription.id
                    results.append(res)
                    break
            download_items[shows[0].name] = results
        return download_items

    def download_latest_episodes_to_clipboard(self, items):
        items_string = '\n'.join(items)
        clipboard = gtk.clipboard_get()
        clipboard.set_text(items_string)
        clipboard.store()

    def download_latest_episodes(self, username):
        download_queue = self.check_for_updates(username)
        download_items = self.get_download_links(download_queue)
        items = []
        session = Session()
        config = ConfigParser.ConfigParser()
        config.read(SubscriptionAdapter.subscription_file)
        for show in download_items.keys():
            for item in download_items[show]:
                items.append(item['download_url'])
                subscription = session.query(Subscription).\
                filter(Subscription.id == item['subscription_id']).first()
                subscription.last_downloaded_episode_id = item['episode_id']
                episode = session.query(Episode).\
                filter(Episode.id == item['episode_id']).first()
                logging.info(item['download_url'])
                config.set(str(show), 'season', episode.season_num)
                config.set(str(show), 'episode', episode.ep_num)
                config.set(str(show), 'last', episode.air_date)
        with open(SubscriptionAdapter.subscription_file, 'wb') as configfile:
            config.write(configfile)
        session.commit()
        return items


class OptionsAdapter(object):
    _subscription_file = os.path.join(cherrypicker.data_dir, 'options.cfg')
    _options_manager = None

    def __init__(self):
        self._options_manager = OptionsManager()

    def generate_default_option_file(self):
        options = ConfigParser.RawConfigParser()
        options.add_section('hoster')
        options.set('hoster', 'rapidshare', 'true')
        options.add_section('release_groups')
        options.set('release_groups', 'afg', 'true')
        options.add_section('quality')
        options.set('quality', 'hdtv', 'true')
        try:
            with open(self._subscription_file, 'wb') as configfile:
                options.write(configfile)
        except IOError:
            raise OptionFileError(self, 'Cannot write to file options.cfg.')

    def load_options_from_file(self):
        options = ConfigParser.RawConfigParser()
        try:
            options.readfp(open(self._subscription_file))
        except IOError as e:
            raise OptionFileError(self, 'Cannot read from options.cfg.')
        list_sections = ['hoster', 'release_groups', 'quality']
        for section in list_sections:
            items = []
            for item, value in options.items(section):
                if value == 'true':
                    items.append(item)
            self._options_manager.__dict__[section] = items


    def save_options_to_file(self):
        raise NotImplementedError


class OptionsManager(object):
    """ Represents user options, is a singleton. """
    __single = None

    def __new__(cls, *args, **kwargs):
        if cls != type(cls.__single):
            cls.__single = object.__new__(cls, *args, **kwargs)
        return cls.__single

#########
# main user interface

def generate_show_template(args):
    entity_manager = EntityManager(Base)
    entity_manager.connect_db()
    __ = entity_manager.create_console_user()
    sca = SubscriptionAdapter(entity_manager)
    sca.generate_subscription_file_template()

def download_new_episodes(args):
    entity_manager = EntityManager(Base)
    entity_manager.connect_db()
    __ = entity_manager.create_console_user()
    sca = SubscriptionAdapter(entity_manager)
    sca.load_subscriptions_from_file()
    scm = SubscriptionManager()
    items = scm.download_latest_episodes('console')
    if args.clipboard:
        scm.download_latest_episodes_to_clipboard(items)

def update_shows(args):
    entity_manager = EntityManager(Base)
    entity_manager.connect_db()
    __ = entity_manager.create_console_user()
    sca = SubscriptionAdapter(entity_manager)
    sca.load_subscriptions_from_file()
    sca.update_subscription_file()

if __name__ == '__main__':
    oa = OptionsAdapter()
    #oa.generate_default_option_file()
    oa.load_options_from_file()
    logging.basicConfig(format='%(message)s', level=logging.INFO)
    parser = argparse.ArgumentParser()
    group_verbosity = parser.add_mutually_exclusive_group()
    group_verbosity.add_argument('-v', '--verbose', action='store_true')
    group_verbosity.add_argument('-q', '--quiet', action='store_true')
    parser.add_argument('-f', '--force', action='store_true')
    parser.add_argument('-c', '--clipboard',
        help='copy download links to system clipboard',
        action='store_true')
    group_actions = parser.add_mutually_exclusive_group()
    group_actions.add_argument('-t', '--generate-show-template',
        help='generate template file',
        action='store_true')
    group_actions.add_argument('-u', '--update-shows',
        help='add running shows to subscription file',
        action='store_true')
    group_actions.add_argument('-d', '--download',
        help='get new download links of subscribed shows',
        action='store_true')
    args = parser.parse_args()

    # check for action parameters and act accordingly
    if args.generate_show_template:
        generate_show_template(args)
        sys.exit(0)
    if args.update_shows:
        update_shows(args)
        sys.exit(0)
    if args.download:
        download_new_episodes(args)
        sys.exit(0)