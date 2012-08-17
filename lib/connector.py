from datetime import date, datetime
import re
import urllib
import urllib2
from BeautifulSoup import BeautifulSoup
import xml.etree.ElementTree as et


class ConnectorCache(object):
    """ Singleton which caches network responses from connected apis. """
    _data_container = {}
    __single = None

    def __new__(cls, *args, **kwargs):
        if cls != type(cls.__single):
            cls.__single = object.__new__(cls, *args, **kwargs)
        return cls.__single

    def getDataItem(self, item):
        data_item = None
        if item in self._data_container:
            data_item = self._data_container[item]
        return data_item

    def setDataItem(self, item, obj):
        self._data_container[item] = obj


class Connector(object):
    """ Abstract base class for tv information api services."""

    _service_base_urls = {}
    _service_api_key = ''
    _cache = None

    def __init__(self):
        # the connector cache is a singleton,
        # all connectors cache into the same container
        self._cache = ConnectorCache()

    def getDataItem(self, item):
        return self._cache.getDataItem(item)

    def setDataItem(self, item, obj):
        self._cache.setDataItem(item, obj)

class ShowConnector(Connector):
    pass

class EpisodeConnector(Connector):
    pass

class CatalogueConnector(Connector):
    """ Retrieve tv listings.
        Abstract class which defines the connector
        api for catalogue entities.
    """

    def current_shows(self):
        """ Retrieve data for shows which are currently airing."""
        raise NotImplementedError


class EztvConnector(CatalogueConnector):
    """ Retrieves show data from eztv.it. """

    _service_base_urls = { 'base': 'http://eztv.it/showlist/' }

    def current_shows(self):
        """ Retrieve data for shows which are currently airing."""

        show_data =  self.getDataItem('current_shows')
        if not show_data:
            show_data = self._scrape(self._service_base_urls['base'])
        if show_data:
            self.setDataItem('current_shows', show_data)
        return show_data

    def _scrape(self, url):
        shows = []
        try:
            soup = BeautifulSoup(urllib2.urlopen(url))
        except:
            raise IOError
        all_shows = soup.findAll('a', {'class': 'thread_link'})
        for show in all_shows:
            if 'Airing' in show.parent.parent.font.text:
                if not 'Irregularly' in show.parent.parent.font.text:
                    show_name = show.text.split(',', 1)
                    shows.append(show_name[0])
        return shows


class TvrageConnector(ShowConnector):
    """ Retrieve detailed show and episode info from tvrage.com. """

    _service_api_key = 'mKu5LRsqNomqFnQrqBxa'
    _service_base_urls = {
            'full_search': 'http://services.tvrage.com/feeds/full_search.php?',
            'full_show_info': 'http://services.tvrage.com/feeds/full_show_info.php?',
            'search': 'http://services.tvrage.com/feeds/search.php?',
            'full_schedule': 'http://services.tvrage.com/myfeeds/fullschedule.php?'
            }

    def update(self, show_name):
        parameters = {'sid': self._findShowId(show_name)}
        request_url = self._service_base_urls['full_show_info'] + urllib.urlencode(parameters)
        file_handle = urllib2.urlopen(request_url)
        show_data = self._parse(file_handle)
        return show_data

    def update_episodes(self, show_id):
        parameters = {'sid': show_id}
        requestUrl = self._service_base_urls['full_show_info'] + urllib.urlencode(parameters)
        episode_data = self._parse_episodes(urllib2.urlopen(requestUrl))
        return episode_data

    def current_schedule(self):
        parameters = {'key': self._service_api_key}
        requestUrl = self._service_base_urls['full_schedule']+ urllib.urlencode(parameters)
        return self._parse_schedule(urllib2.urlopen(requestUrl))

    def _parse_episodes(self, fileHandle):
        tree = et.parse(fileHandle)
        root = tree.getroot()
        episode_data = []
        seasons = root.findall('Episodelist/Season')
        for season in seasons:
            for episode in season.findall('episode'):
                year, month, day = episode.findtext('airdate').split('-')
                ep = {
                    'airdate': date(int(year), int(month), int(day)),
                    'epnum': int(episode.findtext('seasonnum')),
                    'num': int(episode.findtext('epnum')),
                    'seasonnum': int(season.attrib['no']),
                    'link': episode.findtext('link'),
                    'title': episode.findtext('title'),
                    'screencap': episode.findtext('screencap')
                }
                episode_data.append(ep)
        return episode_data

    def _parse(self, file_handle):
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                    'Friday', 'Saturday', 'Sunday']
        tree = et.parse(file_handle)
        root = tree.getroot()
        # handle time with timezone, convert to utc
        timezone_components = root.findtext('timezone').split(' ')
        airtime_components = root.findtext('airtime').split(':')
        airhours_utc = int(airtime_components[0]) - int(re.sub('GMT', '', timezone_components[0]))
        if timezone_components[1] == '+DST':
            airhours_utc -= 1
        weekday_utc_ind = weekdays.index(root.findtext('airday'))
        if airhours_utc > 23:
            weekday_utc_ind += 1
        elif airhours_utc < 0:
            weekday_utc_ind -= 1
        weekday_utc_ind %= 7
        airday_utc = weekdays[weekday_utc_ind]
        airhours_utc = "%s:%s" % (airhours_utc % 24, airtime_components[1])

        show_data = {
            'showid': root.findtext('showid'),
            'airday' : airday_utc,
            'airhours' : airhours_utc,
            'showlink': root.findtext('showlink'),
            'classification': root.findtext('classification'),
            'totalseasons': root.findtext('totalseasons'),
            'status': root.findtext('status'),
            'ended': root.findtext('ended'),
            'started': root.findtext('started'),
            'origin_country': root.findtext('origin_country'),
            'image': root.findtext('image'),
            'runtime': root.findtext('runtime'),
            }
        return show_data

    def _findShowId(self, search_term):
        parameters = {'show': search_term}
        requestUrl = self._baseUrls['search'] + urllib.urlencode(parameters)
        tree = et.parse(urllib2.urlopen(requestUrl))
        shows = tree.getiterator('show')
        return shows[0].findtext('showid')

    def _parse_schedule(self, response):
        schedule_data = []
        tree = et.parse(response)
        days = tree.getroot().findall('DAY')
        for day in days:
            times = day.getiterator('time')
            for time in times:
                shows = time.getiterator('show')
                show_slots = []
                for show in shows:
                    show_slot = {'name': show.attrib.get('name'),
                                 'title': show.findtext('title'),
                                 'ep': show.findtext('ep'),
                                 'link': show.findtext('link'),
                                 'network': show.findtext('network')}
                    show_slots.append(show_slot)
                datetime_string = (day.attrib.get('attr') + ' ' + time.attrib.get('attr'))
                datetime_object = datetime.strptime(datetime_string, '%Y-%m-%d %I:%M %p')
                slot_items = {datetime_object: show_slots}
                schedule_data.append(slot_items)
        return schedule_data