import os
import re
import sys
import ast
from redis import Redis
from random import SystemRandom

from bloody_hell_bot.core.request import BloodyHellRequest
from bloody_hell_bot.dictionaries.dictionary import WordNotFound, DefinitionType
from bloody_hell_bot.dictionaries.aonaware import AonawareDictionary
from bloody_hell_bot.dictionaries.glosbe import GlosbeDictionary
from bloody_hell_bot.dictionaries.urbandict import UrbanDictionary
from bloody_hell_bot.dictionaries.wordnik import WordnikDictionary
from bloody_hell_bot.dictionaries.yadict import YandexDictionary
from bloody_hell_bot.subtitles.opensub import OpenSubtitlesProvider, Subtitles
from bloody_hell_bot.core.nlp import NLPHelper


class BloodyHellApp:

    def __init__(self, config):
        self.config = config
        self.rnd = SystemRandom()

        self.db = Redis.from_url(self.config.REDIS_URL)
        self.prefix = config.REDIS_PREFIX

        self.aonaware = AonawareDictionary()
        self.glosbe = GlosbeDictionary()
        self.urban = UrbanDictionary(api_key=config.URBAN_DICT_API_KEY)
        self.wordnik = WordnikDictionary(api_key=config.WORDNIK_API_KEY)
        self.yadict = YandexDictionary(api_key=config.YADICT_API_KEY)

        self.opensub = OpenSubtitlesProvider(
            username=config.OPENSUB_USERNAME,
            password=config.OPENSUB_PASSWORD
        )
        self.nlp = NLPHelper()

    def initialize(self):
        sentinel_key = '%s:sentinel' % self.prefix
        if self.db.exists(sentinel_key):
            return

        self.db.set(sentinel_key, '1')

        pathname = os.path.dirname(sys.argv[0])
        for preset in ['topwords', 'cognates', 'functionals']:
            key = '%s:%s' % (self.prefix, preset)
            path = '%s/%s.txt' % (pathname, preset)

            with open(path) as f:
                words_list = f.read().splitlines()
                self.db.sadd(key, *words_list)

    def get_state(self, user_id):
        key = '%s:user:%s:state' % (self.prefix, user_id)
        if self.db.exists(key):
            return self.db.get(key).decode()
        return 'newbie'

    def set_state(self, user_id, state):
        key = '%s:user:%s:state' % (self.prefix, user_id)
        self.db.set(key, state)

    def init_vocabulary(self, user_id) -> int:
        key = '%s:user:%s:vocabulary' % (self.prefix, user_id)
        if self.db.scard(key) > 0:
            return 0

        keys = [
            self.prefix + k
            for k in ['topwords', 'cognates', 'functionals']
        ]
        return self.db.sunionstore(key, keys)

    def get_vocabulary(self, user_id):
        key = '%s:user:%s:vocabulary' % (self.prefix, user_id)
        data = self.db.smembers(key)
        stems = list(map(lambda x: self.nlp.get_stem(x.decode()), data))
        return stems

    def get_subtitles(self, hash_key, query=None, index=0) -> Subtitles:
        key = '%s:cache:%s' % (self.prefix, hash_key)
        if not self.db.exists(key):
            if not query:
                raise ValueError('Query is not specified')

            subtitles_list = self.opensub.get_subtitles_list(query)
            if subtitles_list:
                data = list(map(lambda x: x.raw, subtitles_list))
                self.db.lpush(key, *data)
                return subtitles_list[index]

            self.db.lpush(key, 'None')
        else:
            data = ast.literal_eval(self.db.lindex(key, index).decode())
            return Subtitles(data)

    def get_collection_length(self, name):
        key = '%s:cache:%s' % (self.prefix, name)
        return self.db.llen(key)

    def import_unknown_words(self, user_id, name, text) -> int:
        key = '%s:cache:%s' % (self.prefix, name)
        if not self.db.exists(key):
            known_stems = self.get_vocabulary(user_id)
            scored_words = self.nlp.split_text(text)
            unknown_words = [
                (word, score)
                for word, stem, score in scored_words
                if stem not in known_stems
            ]

            for word, score in unknown_words:
                self.db.zincrby(key, word, score)
        else:
            unknown_words = self.db.zrange(key, 0, -1, withscores=True)
            unknown_words = [(word.decode(), score) for word, score in unknown_words]

        for word, score in unknown_words:
            self.db.zincrby('%s:user:%s:study' % (self.prefix, user_id), word, score)

        return len(unknown_words)

    def get_word_to_study(self, user_id):
        key = '%s:user:%s:study' % (self.prefix, user_id)
        if self.db.zcard(key) == 0:
            return None

        word = self.db.zrange(key, 0, 0)[0].decode()
        return word

    def set_known_word(self, user_id, word):
        self.db.zrem('%s:user:%s:study' % (self.prefix, user_id), word)
        self.db.sadd('%s:user:%s:vocabulary' % (self.prefix, user_id), word)

    def get_word_card(self, word):
        key = '%s:cards' % self.prefix
        card = dict()

        if not self.db.hexists(key, word):
            for dictionary in [self.aonaware, self.urban, self.wordnik, self.yadict]:
                try:
                    card = dictionary.get_info(word)
                except WordNotFound:
                    continue
                else:
                    break

            if card:
                self.db.hset(key, word, card)
        else:
            card = ast.literal_eval(self.db.hget(key, word).decode())

        return card

    def create_tests(self, user_id, word):
        key = '%s:user:%s:study' % (self.prefix, user_id)
        self.db.zrem(key, word)

        tests = []
        card = self.get_word_card(word)

        if card.get(DefinitionType.SYNONIM):
            tests.append(self.create_synonims_test(user_id, word))

        tests.append(self.create_fill_sentence_choice_test(user_id, card))
        tests.append(self.create_fill_sentence_prefix_test(user_id, card))

        for test in tests:
            self.db.zadd(key, test, self.rnd.randint(0, 500))

        return tests

    def add_word_association(self, req: BloodyHellRequest, word):
        key = '%s:user:%s:%s' % (self.prefix, req.user_id, word)
        association = {
            'word': word,
            'type': req.msg_type
        }

        if req.msg_type == 'text':
            association['value'] = '<pre>%s</pre>' % req.msg['text']
        elif req.msg_type == 'photo':
            association['value'] = req.msg['photo'][-1]['file_id']
        elif req.msg_type == 'document':
            association['value'] = req.msg['document']['file_id']

        self.db.lpush(key, association)

    def pop_word_association(self, user_id, word):
        key = '%s:user:%s:%s' % (self.prefix, user_id, word)
        count = self.db.llen(key)

        if count > 1:
            return ast.literal_eval(self.db.lpop(key).decode())
        if count > 0:
            return ast.literal_eval(self.db.lindex(key, 0).decode())

    def create_fill_sentence_choice_test(self, user_id, card: dict, answers_count=6):
        answers = [
            w.decode()
            for w in self.db.srandmember('%s:topwords' % self.prefix, answers_count - 1)
        ]
        answers.append(card['word'])

        stem = self.nlp.get_stem(card['word'])
        gap = '_' * len(card['word'])
        sentence = self.rnd.choice(card.get(DefinitionType.EXAMPLE, []))

        test = {
            'title': 'Select the most suitable word (form insensitive):',
            'question': re.sub('%s\w*' % stem, gap, sentence, flags=re.IGNORECASE),
            'answers': answers,
            'correct': stem,
            'word': card['word'],
            'type': '0'
        }

        association = self.pop_word_association(user_id, card['word'])
        if association:
            test['association'] = association

        return test

    def create_fill_sentence_prefix_test(self, user_id, card: dict, prefix=3):
        stem = self.nlp.get_stem(card['word'])
        gap = card['word'][:prefix] + '_' * len(card['word'])
        sentence = self.rnd.choice(card.get(DefinitionType.EXAMPLE, []))

        test = {
            'title': 'Write the word, beginning with letters (form insensitive):',
            'question': re.sub('%s\w*' % stem, gap, sentence, flags=re.IGNORECASE),
            'correct': stem,
            'word': card['word'],
            'type': '1'
        }

        association = self.pop_word_association(user_id, card['word'])
        if association:
            test['association'] = association

        return test

    def create_synonims_test(self, user_id, card):
        answers = list(map(
            lambda x: self.nlp.get_stem(x),
            card.get(DefinitionType.SYNONIM)
        ))

        test = {
            'title': 'Write any synonym(s) to this word you can remember:',
            'question': card['word'],
            'correct': answers,
            'word': card['word'],
            'type': '2'
        }

        association = self.pop_word_association(user_id, card['word'])
        if association:
            test['association'] = association

        return test

    def update_test(self, user_id, test):
        card = self.get_word_card(test['word'])
        if test['type'] == '0':
            return self.create_fill_sentence_choice_test(user_id, card)
        elif test['type'] == '1':
            return self.create_fill_sentence_prefix_test(user_id, card)
        return test

    def get_test(self, user_id):
        key = '%s:user:%s:test' % (self.prefix, user_id)
        if self.db.zcard(key) == 0:
            return None

        return ast.literal_eval(self.db.zrange(key, 0, 0)[0].decode())

    def check_test_answer(self, user_id, answer):
        key = '%s:user:%s:test' % (self.prefix, user_id)
        value = self.db.zrange(key, 0, 0)[0]
        score = self.db.zscore(key, value)

        test = ast.literal_eval(value.decode())
        answer_stems = list(map(self.nlp.get_stem, self.nlp.get_tokens(answer)))

        self.db.zrem(key, value)

        if any(a in test['correct'] for a in answer_stems):
            return True

        if score > 1000:
            self.db.zincrby(
                '%s:user:%s:study' % (self.prefix, user_id), test['word'], 0.0001)
        else:
            test = self.update_test(user_id, test)
            self.db.zincrby(key, test, score + 500)

        return False
