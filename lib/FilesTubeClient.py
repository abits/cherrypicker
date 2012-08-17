import sys
import urllib, urllib2
import xml.etree.ElementTree as et
from BeautifulSoup import BeautifulSoup
import threading
import Queue
import logging
import re


class FilesTubeClient:
    def __init__(self):
        self._apiKey = '7c15619be31a126ceeaf7fcc070588f7'
        self._baseUrl = 'http://api.filestube.com/?'
        self._resultsQueue = Queue.Queue()
        self._threads = []
        self._hostCodes = {'uploaded': '24',
                           'wupload': '49',
                           'mediafire': '15',
                           'rapidshare': '1',
                           'depositfiles': '12',
                           'hotfile': '27',
                           'letitbit': '25',
                           'oron': '43',
                           'netload': '22'}

    def update(self, phrase, extension='avi', sort='dd', host='uploaded'):
        parameters = {'key': self._apiKey,
                      'phrase': phrase,
                      'extension': extension,
                      'sort': sort,
                      'hosting': self._hostCodes[host]}
        requestUrl = self._baseUrl + urllib.urlencode(parameters)
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
        details = {}
        details['detailsUrl'] = hit.findtext('details')
        details['downloadUrl'] = self._scrape(details['detailsUrl'])
        details['addedDate'] = hit.findtext('added')
        details['size'] = hit.findtext('size')
        details['name'] = hit.findtext('name')
        details['extension'] = hit.findtext('extension')
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
    client = FilesTubeClient()
    res = client.update('The Office 8x18', host='netload')
    print res
    print client.getResults()
    sys.exit()



