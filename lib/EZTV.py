import urllib2
from BeautifulSoup import BeautifulSoup
from backend.entity import Show

class EZTV:
    base_url = 'http://eztv.it/showlist/'

    def current_shows(self):
        requestUrl = self.base_url
        show_data = self._scrape(requestUrl)
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

    def update_shows(self, connector, show_names):
        for show_name in show_names:
            show = Show.objects.get_or_create(name=show_name)
            show.update(connector)
            show.save()

if __name__ == '__main__':
    testDriver = EZTV()
    print testDriver.current_shows()
