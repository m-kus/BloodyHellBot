import re
import requests

from bloody_hell_bot.dictionaries.dictionary import Dictionary, DefinitionType, WordNotFound


class UrbanDictionary(Dictionary):

    def __init__(self, api_key, min_len=15, max_len=128):
        self.api_key = api_key
        self.min_len = min_len
        self.max_len = max_len

    def get_data(self, word):
        res = requests.get(
            url='https://mashape-community-urban-dictionary.p.mashape.com/define',
            params={
                'term': word
            },
            headers={
                'X-Mashape-Key': self.api_key,
                'Accept': 'text/plain'
            }
        )
        data = res.json()
        if not data.get('list'):
            raise WordNotFound

        return data

    def iter_definitions(self, word):
        data = self.get_data(word)

        def make_sentence(string):
            string = re.sub('[\[\]]', '', string)
            string = re.sub('[\n\r]?\n', '\n', string)
            string = string.strip().strip('"\'`').strip()
            if string and string[-1] not in '.!?':
                string += '.'
            return string.capitalize()

        for item in data:
            if item.get('example'):
                text = make_sentence(item['example'])
                if self.min_len < len(text) < self.max_len:
                    yield DefinitionType.EXAMPLE, text

            if item.get('definition'):
                text = make_sentence(item['definition'])
                if text.startswith('/'):
                    pron, _, text = text.split('\n', maxsplit=3)
                    yield DefinitionType.PRONUNCIATION, pron
                    yield DefinitionType.MEANING, text
                else:
                    yield DefinitionType.MEANING, text
