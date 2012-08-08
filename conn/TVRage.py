import urllib, urllib2
import xml.etree.ElementTree as et
from datetime import time, datetime
from datetime import date
import time, re

class TVRage:
    def __init__(self):
        self._tvr_api_key = 'mKu5LRsqNomqFnQrqBxa'
        self._baseUrls = {
            'full_search': 'http://services.tvrage.com/feeds/full_search.php?',
            'full_show_info': 'http://services.tvrage.com/feeds/full_show_info.php?',
            'search': 'http://services.tvrage.com/feeds/search.php?',
            'full_schedule': 'http://services.tvrage.com/myfeeds/fullschedule.php?'
        }

    def update(self, show_name):
        parameters = {'sid': self._findShowId(show_name)}
        request_url = self._baseUrls['full_show_info'] + urllib.urlencode(parameters)
        file_handle = urllib2.urlopen(request_url)
        show_data = self._parse(file_handle)
        return show_data

    def update_episodes(self, show_id):
        parameters = {'sid': show_id}
        requestUrl = self._baseUrls['full_show_info'] + urllib.urlencode(parameters)
        episode_data = self._parse_episodes(urllib2.urlopen(requestUrl))
        return episode_data

    def current_schedule(self):
        parameters = {'key': self._tvr_api_key}
        requestUrl = self._baseUrls['full_schedule']+ urllib.urlencode(parameters)
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
            airhours_utc = airhours_utc - 1
        weekday_utc_ind = weekdays.index(root.findtext('airday'))
        if airhours_utc > 23:
            weekday_utc_ind = weekday_utc_ind + 1
        elif airhours_utc < 0:
            weekday_utc_ind = weekday_utc_ind - 1
        weekday_utc_ind = weekday_utc_ind % 7
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
