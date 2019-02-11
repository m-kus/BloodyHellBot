class WordNotFound(Exception):
    pass


class DefinitionType:
    MEANING = 'meaning'
    SYNONIM = 'synonim'
    EXAMPLE = 'example'
    PRONUNCIATION = 'pronunciation'
    TRANSLATION = 'translation'

    @classmethod
    def values(cls):
        return [cls.MEANING, cls.SYNONIM, cls.EXAMPLE, cls.PRONUNCIATION, cls.TRANSLATION]


class Dictionary:

    def iter_definitions(self, word):
        raise NotImplementedError

    def get_info(self, word) -> dict:
        card = {
            definition_type: list()
            for definition_type in DefinitionType.values()
        }
        for definition_type, text in self.iter_definitions(word):
            card[definition_type].append(text)

        card.update(word=word)
        return card
