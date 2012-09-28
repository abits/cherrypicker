from datetime import  datetime, timedelta
import string
import sys
import urllib
import urllib2
from BeautifulSoup import BeautifulSoup
import xml.etree.ElementTree as et
import threading
import Queue
import logging


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
    """ Defines the api for show data. """
    show_data = {
        'show_id': '',
        'air_day' : '',
        'air_hours' : '',
        'show_link': '',
        'classification': '',
        'total_seasons': '',
        'status': '',
        'ended': '',
        'started': '',
        'origin_country': '',
        'image': '',
        'runtime': '',
        }

class EpisodeConnector(Connector):
    """ Defines the api for episode data.

        Array keys must match table columns from corresponding model.
    """
    episode_data = {
        'num': '',
        'ep_num': '',
        'season_num': '',
        'air_date': '' ,
        'link': '',
        'title': '',
        'screen_cap': '',
    }

class CatalogueConnector(Connector):
    """ Retrieve tv listings.
        Abstract class which defines the connector
        api for catalogue entities.
    """

    def current_shows(self):
        """ Retrieve data for shows which are currently airing."""
        raise NotImplementedError


class SearchConnector(Connector):
    """ Retrieve file download links.
        Abstract class which defines the connector
        api for search requests.
    """

class EztvCatalogueConnector(CatalogueConnector):
    """ Retrieves show data from eztv.it. """

    _service_base_urls = { 'base': 'http://eztv.it/showlist/' }

    def current_shows(self):
        """ Retrieve data for shows which are currently airing."""

        show_data =  self.getDataItem('ezt_catalogue_current_shows')
        if not show_data:
            show_data = self._scrape(self._service_base_urls['base'])
        if show_data:
            self.setDataItem('ezt_catalogue_current_shows', show_data)
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
                    show_name = show.text.split(',')
                    if len(show_name) > 1:
                        show_name_complete = '%s %s' % (show_name[1], show_name[0])
                    else:
                        show_name_complete = show_name[0]
                    shows.append(show_name_complete.strip())
        return shows

class TvrageCatalogueConnector(CatalogueConnector):
    """ Retrieve schedule info from tvrage.com. """

    _service_api_key = 'mKu5LRsqNomqFnQrqBxa'
    _service_base_urls = {
        'full_search': 'http://services.tvrage.com/feeds/full_search.php?',
        'full_show_info': 'http://services.tvrage.com/feeds/full_show_info.php?',
        'search': 'http://services.tvrage.com/feeds/search.php?',
        'full_schedule': 'http://services.tvrage.com/myfeeds/fullschedule.php?'
    }

    def current_shows(self):
        schedule_data = self.getDataItem('tvr_catalogue_current_shows')
        if not schedule_data:
            parameters = {'key': self._service_api_key}
            requestUrl = self._service_base_urls['full_schedule']+ urllib.urlencode(parameters)
            schedule_data = self._parse_schedule(urllib2.urlopen(requestUrl))
        if schedule_data:
            self.setDataItem('tvr_catalogue_current_shows', schedule_data)
        return schedule_data

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

class TvrageEpisodeConnector(EpisodeConnector):
    """ Retrieve detailed episode info from tvrage.com. """

    _service_api_key = 'mKu5LRsqNomqFnQrqBxa'
    _service_base_urls = {
        'full_search': 'http://services.tvrage.com/feeds/full_search.php?',
        'full_show_info': 'http://services.tvrage.com/feeds/full_show_info.php?',
        'search': 'http://services.tvrage.com/feeds/search.php?',
        'full_schedule': 'http://services.tvrage.com/myfeeds/fullschedule.php?'
    }

    def update_episodes(self, show):
        parameters = {'sid': show.tvr_id}
        requestUrl = self._service_base_urls['full_show_info'] + urllib.urlencode(parameters)
        episode_data = self._parse_episodes(show, urllib2.urlopen(requestUrl))
        return episode_data

    def _parse_episodes(self, show, fileHandle):
        tree = et.parse(fileHandle)
        root = tree.getroot()
        episode_data = []
        seasons = root.findall('Episodelist/Season')
        for season in seasons:
            for episode in season.findall('episode'):
                ep = {
                    'air_date': self._get_air_date(show, episode.findtext('airdate')),
                    'ep_num': int(episode.findtext('seasonnum')),
                    'num': int(episode.findtext('epnum')),
                    'season_num': int(season.attrib['no']),
                    'link': episode.findtext('link'),
                    'title': episode.findtext('title'),
                    'screen_cap': episode.findtext('screencap')
                }
                episode_data.append(ep)
        return episode_data

    def _get_air_date(self, show, date_value):
        # Find real airtime converted to UTC.  Incorrect timings for past episodes doesn't matter
        # as we only need this datetime to calculate earliest possible release dates for
        # future episodes.
        time, shift, dst = show.airtime.split()
        shift = string.replace(shift, 'GMT', '')
        shift_plus = False
        if shift.find('+'):
            shift_plus = True
        shift = timedelta(hours=int(shift.lstrip('+-')))
        hours, minutes = time.split(':')
        year, month, day = date_value.split('-')
        try:
            air_date = datetime(int(year), int(month), int(day), int(hours), int(minutes), 0, 0)
            if shift_plus:
                air_date += shift
            else:
                air_date -= shift
        except ValueError:
            air_date = None
        return air_date

class TvrageShowConnector(ShowConnector):
    """ Retrieve detailed show info from tvrage.com. """

    _service_api_key = 'mKu5LRsqNomqFnQrqBxa'
    _service_base_urls = {
            'full_search': 'http://services.tvrage.com/feeds/full_search.php?',
            'full_show_info': 'http://services.tvrage.com/feeds/full_show_info.php?',
            'search': 'http://services.tvrage.com/feeds/search.php?',
            'full_schedule': 'http://services.tvrage.com/myfeeds/fullschedule.php?'
            }

    def update_show(self, show_name):
        parameters = {'sid': self._findShowId(show_name)}
        request_url = self._service_base_urls['full_show_info'] + urllib.urlencode(parameters)
        file_handle = urllib2.urlopen(request_url)
        show_data = self._parse(file_handle)
        return show_data

    def _parse(self, file_handle):
        tree = et.parse(file_handle)
        root = tree.getroot()
        # assign the simple stuff
        show_data = {'show_id': self._filter_number(root, 'showid'),
                     'show_link': self._filter_phrase(root, 'showlink'),
                     'classification': self._filter_phrase(root, 'classification'),
                     'total_seasons': self._filter_number(root, 'totalseasons'),
                     'status': self._filter_phrase(root, 'status'),
                     'ended': self._get_date_string(root, 'ended'),
                     'started': self._get_date_string(root, 'started'),
                     'origin_country': self._filter_phrase(root, 'origin_country'),
                     'image': self._filter_phrase(root, 'image'),
                     'runtime': self._filter_number(root, 'runtime'),
                     'air_day': self._filter_phrase(root, 'airday'),
                     'air_hours': self._get_airtime(root)}
        return show_data

    def _filter_phrase(self, root, phrase):
        return_value = None
        phrase_string = root.findtext(phrase)
        if phrase_string:
            return_value = root.findtext(phrase)
        return return_value

    def _filter_number(self, root, number):
        return_value = None
        number_string = root.findtext(number)
        if number_string:
            return_value = int(number_string)
        return return_value

    def _get_airtime(self, root):
        airtime = '%s %s' % (root.findtext('airtime'), root.findtext('timezone'))
        return airtime

    def _get_date_string(self, root, phrase):
        date_string = None
        months = { 'Jan': '01',
                   'Feb': '02',
                   'Mar': '03',
                   'Apr': '04',
                   'May': '05',
                   'Jun': '06',
                   'Jul': '07',
                   'Aug': '08',
                   'Sep': '09',
                   'Oct': '11',
                   'Nov': '11',
                   'Dec': '12' }
        date_phrase = root.findtext(phrase)
        try:
            month_word, day, year = date_phrase.split('/')
            month = months[month_word]
            date_string = '%s-%s-%s' % (year, month, day)
        except:
            pass
        return date_string

    def _get_ended(self, root):
        pass

    def _findShowId(self, search_term):
        show_id = None
        parameters = {'show': search_term}
        requestUrl = self._service_base_urls['search'] + urllib.urlencode(parameters)
        tree = et.parse(urllib2.urlopen(requestUrl))
        shows = tree.getiterator('show')
        discontinued = ['Pilot Rejected', 'Canceled/Ended']
        # use the first match which is not a discontinued show
        for show in shows:
            status = show.findtext('status')
            if status in discontinued:
                continue # don't use discontinued shows
            else:
                show_id = show.findtext('showid')
                break # we use the first match

        return show_id

class FilesTubeConnector(SearchConnector):
    _service_api_key = '7c15619be31a126ceeaf7fcc070588f7'
    _service_base_urls = 'http://api.filestube.com/?'
    _host_codes = {'uploaded': '24',
                  'wupload': '49',
                  'mediafire': '15',
                  'rapidshare': '1',
                  'depositfiles': '12',
                  'hotfile': '27',
                  'letitbit': '25',
                  'oron': '43',
                  'netload': '22',
                  'rapidgator': '64'}

    def __init__(self):
        super(FilesTubeConnector, self).__init__()
        self._resultsQueue = Queue.Queue()
        self._threads = []

    def update(self, phrase, extension='avi', sort='dd', host='uploaded'):
        parameters = {'key': self._service_api_key,
                      'phrase': phrase,
                      'extension': extension,
                      'sort': sort,
                      'hosting': self._host_codes[host]}
        requestUrl = self._service_base_urls + urllib.urlencode(parameters)
        self._parse(urllib2.urlopen(requestUrl))
        return requestUrl

    def getResults(self):
        results = []
        while 1:
            try:
                results.append(self._resultsQueue.get(block=False))
            except:
                return results

    def getOneUrl(self):
        results = self.getResults()
        returnValue = ''
        if len(results) > 0:
            returnValue = results[0]['downloadUrl']
        return returnValue

    def _parse(self, fileHandle):
        tree = et.parse(fileHandle)
        root = tree.getroot()
        hits = root.getiterator('hits')
        for hit in hits:
            t = threading.Thread(target=self._retrieveResults, args=(hit,))
            t.start()
            self._threads.append(t)
        for thread in self._threads:
            thread.join()

    def _retrieveResults(self, hit):
        details = { 'details_url': hit.findtext('details'),
                    'download_url': self._scrape(hit.findtext('details')),
                    'added_date': hit.findtext('added'),
                    'size': hit.findtext('size'),
                    'name': hit.findtext('name'),
                    'extension': hit.findtext('extension') }
        self._resultsQueue.put(details, timeout=3000)

    def _scrape(self, url):
        link = ''
        try:
            html = urllib2.urlopen(url)
            soup = BeautifulSoup(html)
            link = soup.find(id='copy_paste_links').string
        except:
            logging.error("LinkFetcher: Network connection error.")
        return link.rstrip()

if __name__ == '__main__':
    client = FilesTubeConnector()
    res = client.update('The Office 9x01', host='rapidgator')
    print res
    print client.getResults()
    sys.exit()