import requests

from bloody_hell_bot.dictionaries.dictionary import Dictionary, DefinitionType, WordNotFound


class YandexDictionary(Dictionary):

    def __init__(self, api_key, lang='en-ru'):
        self.api_key = api_key
        self.lang = lang

    def get_data(self, word):
        res = requests.get('https://dictionary.yandex.net/api/v1/dicservice.json/lookup', params={
            'key': self.api_key,
            'lang': self.lang,
            'text': word
        })
        data = res.json()
        if not data.get('def'):
            raise WordNotFound

        return data

    def iter_definitions(self, word):
        data = self.get_data(word)

        for item in data['def']:
            if item.get('ts'):
                yield DefinitionType.PRONUNCIATION, item['ts']

            for translation in item.get('tr', []):
                for mean in translation.get('mean', []):
                    if word not in mean:
                        yield DefinitionType.SYNONIM, mean['text']

                yield DefinitionType.TRANSLATION, translation['text']
