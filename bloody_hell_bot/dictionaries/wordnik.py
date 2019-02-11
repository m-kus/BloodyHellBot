import requests

from bloody_hell_bot.dictionaries.dictionary import Dictionary, DefinitionType, WordNotFound


class WordnikDictionary(Dictionary):

    def __init__(self, api_key, limit=10):
        self.api_key = api_key
        self.limit = limit

    def get_data(self, word, kind):
        res = requests.get('http://api.wordnik.com/v4/word.json/{}/{}'.format(word, kind), params={
            'limit': self.limit,
            'includeRelated': 'true',
            'sourceDictionaries': 'all',
            'useCanonical': 'false',
            'includeTags': 'false',
            'api_key': self.api_key
        })
        data = res.json()
        if not data:
            raise WordNotFound

        return data

    def iter_definitions(self, word):
        definitions = self.get_data(word, kind='definitions')
        for item in definitions:
            yield DefinitionType.MEANING, item['text']

        examples = self.get_data(word, kind='examples')
        for item in examples.get('examples', []):
            yield DefinitionType.EXAMPLE, item['text']

        prons = self.get_data(word, kind='pronunciations')
        for item in prons:
            if item['rawType'] == 'arpabet':
                yield DefinitionType.PRONUNCIATION, item['raw']
