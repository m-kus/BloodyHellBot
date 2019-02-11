from os.path import join, dirname
from unittest.mock import patch
from unittest import TestCase
from parameterized import parameterized

from bloody_hell_bot.dictionaries.aonaware import AonawareDictionary


class Response:

    def __init__(self, text):
        self._text = text

    @property
    def text(self):
        return self._text


class TestDictionaries(TestCase):

    @parameterized.expand([
        ('ugly', 'data/aonaware_ugly.xml', 5, 3, 3),
        ('cut', 'data/aonaware_cut.xml', 18, 6, 22),
        ('frame', 'data/aonaware_frame.xml', 5, 12, 7)
    ])
    @patch('requests.get')
    def test_aonaware(self, word, path, meanings, synonims, examples, get):
        with open(join(dirname(__file__), path)) as f:
            text = f.read()

        get.return_value = Response(text)

        dictionary = AonawareDictionary()
        info = dictionary.get_info(word)

        self.assertEqual(meanings, len(info['meaning']))
        self.assertEqual(examples, len(info['example']))
        self.assertEqual(synonims, len(info['synonim']))
