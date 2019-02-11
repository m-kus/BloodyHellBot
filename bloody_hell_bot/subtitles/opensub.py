import re
import zlib
import requests
import collections
from typing import List
from pythonopensubtitles.opensubtitles import OpenSubtitles


class OpenSubtitleSession:

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self._ost = OpenSubtitles()

    def __enter__(self):
        token = self._ost.login(self.username, self.password)
        if not token:
            raise ValueError('Failed to login')

        return self._ost

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ost.logout()


class Subtitles:

    def __init__(self, raw: dict):
        self._raw = raw
        self._text = None

    def __getitem__(self, item):
        return self._raw[item]

    @property
    def text(self):
        if not self._text:
            res = requests.get(self._raw['SubDownloadLink'])
            srt = zlib.decompress(res.content, 16 + zlib.MAX_WBITS)
            srt = srt.decode(self._raw['SubEncoding'])
            srt = re.sub('(\d{2}[:,\d]){4}', '', srt)
            srt = re.sub('(-->)', '', srt)
            srt = re.sub('</?[^>]>', ' ', srt)
            srt = re.sub('\d', '', srt)
            srt = re.sub('\r\n', ' ', srt)
            srt = re.sub('(ecbd|www|opensubtitles)', '', srt)
            self._text = srt
        return self._text

    @property
    def id(self):
        return self._raw['IDSubtitle']

    @property
    def imdb_link(self):
        return 'http://www.imdb.com/title/tt%s/' % (self._raw['IDMovieImdb'])


class OpenSubtitlesProvider:

    def __init__(self, username, password, lang='eng'):
        self.username = username
        self.password = password
        self.lang = lang

    def get_subtitles_list(self, query) -> List[Subtitles]:
        request = {
            'sublanguageid': self.lang,
            'query': query
        }

        params = re.findall('(.*)\s+s(\d+)\s*e(\d+)', query)
        if len(params) > 0:
            request['query'], request['season'], request['episode'] = params[0]

        with OpenSubtitleSession(self.username, self.password) as ost:
            sub_list = ost.search_subtitles([request])

        top_subs = collections.OrderedDict()
        for sub in sub_list:
            if sub['SubFormat'] != 'srt':
                continue

            query_is_series = 'season' in sub['QueryParameters']
            result_is_series = int(sub['SeriesSeason']) > 0
            if query_is_series != result_is_series:
                continue

            name = sub['MovieName']
            if name in top_subs.keys():
                if int(sub['SubDownloadsCnt']) <= int(top_subs[name]['SubDownloadsCnt']):
                    continue

            top_subs[name] = sub

        subtitles = list(map(lambda x: Subtitles(x, query), top_subs.values()))
        return subtitles
