import requests
import re
from lxml import objectify

from bloody_hell_bot.dictionaries.dictionary import Dictionary, WordNotFound, DefinitionType


class AonawareDictionary(Dictionary):

    def __init__(self, dict_id='gcide'):
        self.dict_id = dict_id

    def get_data(self, word):
        res = requests.get(
            url='http://services.aonaware.com/DictService/DictService.asmx/DefineInDict',
            params={
                'dictId': self.dict_id,
                'word': word
            }
        )
        data = objectify.fromstring(res.text.encode('utf-8'))
        if not hasattr(data.Definitions, 'Definition'):
            raise WordNotFound(word)

        return data

    def iter_definitions(self, word):
        data = self.get_data(word)

        article = data.Definitions.Definition[0].WordDefinition.text  # take the first one only
        article = re.sub('\[[^\]]+\]', '', article)
        article = re.sub('\([^\)]+\)', '', article)
        article = re.sub('[\{\}`\']', '', article)
        article = re.sub('etc\.', 'etc', article)
        article = re.sub('\.\s\.\s\.\s', '', article)
        article = re.sub('[0-9]+\.', '', article)
        article = re.sub('\([a-z]\)', '', article)
        article = re.sub('--[A-z\s]+\.?', '', article)
        article = re.sub('[A-Z][a-z]+\.', '', article)

        lines = re.split('\n\n', article)
        lines = map(lambda x: re.sub('[\n\s]+', ' ', x).strip(), lines)

        sentences = map(lambda x: max(re.split('[\.!?\]]', x), key=len).strip(), lines)
        sentences = list(filter(lambda x: len(x) > 3 and x[0].isupper() and '{' not in x, sentences))

        for sentence in sentences:
            parts = re.split('[;:]', sentence)
            parts = list(map(lambda x: x.lstrip().capitalize(), parts))

            if sentence.startswith('Syn:'):
                for part in parts:
                    yield DefinitionType.SYNONIM, part

            elif word not in sentence:
                for part in parts:
                    words = part.split()
                    if len(words) == 1:
                        yield DefinitionType.SYNONIM, part
                    elif len(words) == 2 and words[0] in ['To', 'A']:
                        yield DefinitionType.SYNONIM, part
                    else:
                        yield DefinitionType.MEANING, part

            elif 'as,' not in sentence:
                yield DefinitionType.EXAMPLE, sentence
            else:
                yield DefinitionType.MEANING, sentence
