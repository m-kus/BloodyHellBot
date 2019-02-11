import requests

from bloody_hell_bot.dictionaries.dictionary import Dictionary, WordNotFound, DefinitionType


class GlosbeDictionary(Dictionary):

    def __init__(self, lang='en', min_len=15, max_len=128):
        self.lang = lang
        self.min_len = min_len
        self.max_len = max_len

    def get_data(self, word, offset=0):
        res = requests.get('https://glosbe.com/gapi/tm', params={
            'from': self.lang,
            'dest': self.lang,
            'format': 'json',
            'phrase': word,
            'page': offset + 1
        })
        data = res.json()
        if not data.get('found'):
            raise WordNotFound

        return data

    def iter_definitions(self, word):
        data = self.get_data(word)
        for item in data.get('examples', []):
            text = item['first']
            if self.min_len < text < self.max_len:
                yield DefinitionType.EXAMPLE, item['first']
