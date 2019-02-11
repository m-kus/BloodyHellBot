import telepot
import hashlib
from random import SystemRandom

import bloody_hell_bot.core.views as views
from bloody_hell_bot.core.request import BloodyHellRequest
from bloody_hell_bot.core.app import BloodyHellApp
from bloody_hell_bot.dictionaries.dictionary import DefinitionType


class BloodyHellBot:

    def __init__(self, config):
        self.config = config
        self.app = BloodyHellApp(config)
        self.bot = telepot.Bot(config.BOT_TOKEN)
        self.rnd = SystemRandom()

    def message_loop(self):
        self.app.initialize()
        self.bot.message_loop({
            'chat': lambda x: self.on_chat_dispatch(BloodyHellRequest(x)),
            'callback_query': lambda x: self.on_callback_query_dispatch(BloodyHellRequest(x))
        })

    def start(self, req: BloodyHellRequest):
        self.bot.sendMessage(req.user_id, views.start())

        vocabulary_size = self.app.init_vocabulary(req.user_id)
        if vocabulary_size > 0:
            self.bot.sendMessage(req.user_id, views.initialize(vocabulary_size))

        self.end(req)
        self.help(req)

    def end(self, req: BloodyHellRequest):
        self.app.set_state(req.user_id, state='search')

    def help(self, req: BloodyHellRequest):
        self.bot.sendMessage(req.user_id, views.help())

    def on_search_select(self, req: BloodyHellRequest, hash_key, index):
        self.bot.editMessageText((req.user_id, req.msg_id), req.msg_text)
        self.bot.sendMessage(
            req.user_id, text='Start to download and process subtitle file. It will take a while.')

        subtitles = self.app.get_subtitles(hash_key=hash_key, index=index)
        imported = self.app.import_unknown_words(
            req.user_id, name=subtitles.id, text=subtitles.text)
        self.bot.sendMessage(req.user_id, views.search_import(imported))

    def on_search_navigate(self, req: BloodyHellRequest, hash_key, index):
        subtitles = self.app.get_subtitles(hash_key=hash_key, index=index)
        markup = views.navigate_markup(self.app.get_collection_length(hash_key), hash_key, index)
        self.bot.editMessageText(
            (req.user_id, req.msg_id), text=subtitles.imdb_link, reply_markup=markup)

    def on_search(self, req: BloodyHellRequest):
        hash_key = hashlib.md5(req.msg_text.encode('utf-8')).hexdigest()
        subtitles = self.app.get_subtitles(hash_key=hash_key, query=req.msg_text)
        text = subtitles.text

        if text:
            markup = views.navigate_markup(self.app.get_collection_length(hash_key), hash_key, 0)
        else:
            markup, text = None, 'Sorry, cannot find subtitles. Could be a typo.'

        self.bot.sendMessage(req.user_id, text, reply_markup=markup)

    def study(self, req):
        self.app.set_state(req.user_id, state='study')
        word = self.app.get_word_to_study(req.user_id)

        if word:
            markup = views.known_unknown_markup(word)
        else:
            markup, word = None, 'No more words!'

        if req.msg_type == 'text':
            self.bot.sendMessage(req.user_id, word, reply_markup=markup)
        else:
            self.bot.editMessageText((req.user_id, req.msg_id), word, reply_markup=markup)

    def on_study_known(self, req, word):
        self.app.set_known_word(req.user_id, word)
        self.study(req)

    def on_study_unknown(self, req: BloodyHellRequest, word):
        self.app.set_state(req.user_id, state='study:%s' % word)
        card = self.app.get_word_card(word)

        if card:
            texts = views.study_cards(card)
        else:
            texts = [views.study_notfound(word)]

        self.bot.editMessageText(
            (req.user_id, req.msg_id), text=texts.pop(0), parse_mode='HTML')

        for text in texts:
            self.bot.sendMessage(req.user_id, text, parse_mode='HTML')

        markup = views.study_more_markup(word)
        self.bot.sendMessage(
            req.user_id, text='More examples or go to the /next word.', reply_markup=markup)

    def on_study_more(self, req: BloodyHellRequest, word):
        card = self.app.get_word_card(word)
        example = self.rnd.choice(card.get(DefinitionType.EXAMPLE, []))
        if example and example != req.msg_text:
            markup = views.study_more_markup(word)
            self.bot.editMessageText(
                (req.user_id, req.msg_id), text=example, reply_markup=markup, parse_mode='HTML')

    def on_study_translation(self, req: BloodyHellRequest, word):
        card = self.app.get_word_card(word)
        translations = card.get(DefinitionType.TRANSLATION)
        if translations:
            text = ', '.join(translations)
            if text != req.msg_text:
                markup = views.study_more_markup(word)
                self.bot.editMessageText(
                    (req.user_id, req.msg_id), text=text, reply_markup=markup, parse_mode='HTML')

    def on_study_unknown_end(self, req: BloodyHellRequest, word):
        self.app.create_tests(req.user_id, word)
        self.study(req)

    def on_study(self, req: BloodyHellRequest, word):
        self.app.add_word_association(req.user_id, word)
        self.bot.sendMessage(
            req.user_id, text='Association created! Add another one or go to the /next word.')

    def test(self, req: BloodyHellRequest):
        self.app.set_state(req.user_id, state='test')

        test = self.app.get_test(req.user_id)
        markup = None

        if test:
            if 'association' in test:
                if test['association']['type'] == 'text':
                    self.bot.sendMessage(req.user_id, test['association']['value'], parse_mode='HTML')
                elif test['association']['type'] == 'photo':
                    self.bot.sendPhoto(req.user_id, test['association']['value'])
                elif test['association']['type'] == 'document':
                    self.bot.sendDocument(req.user_id, test['association']['value'])

            if 'answers' in test:
                markup = views.answers_markup(test['answers'])

            view = views.test(test)
        else:
            view = 'No more tests!'

        self.bot.sendMessage(req.user_id, view, reply_markup=markup, parse_mode='HTML')

    def on_test(self, req: BloodyHellRequest):
        correct = self.app.check_test_answer(req.user_id, req.msg_text)
        text = views.test_mark(correct)

        self.bot.sendMessage(req.user_id, text, parse_mode='HTML')
        self.test(req)

    def on_chat_dispatch(self, req: BloodyHellRequest):
        if req.msg_text:
            if req.msg_text.startswith('/end'):
                return self.end(req)
            if req.msg_text.startswith('/help'):
                return self.help(req)
            if req.msg_text.startswith('/start'):
                return self.start(req)
            if req.msg_text.startswith('/study'):
                return self.study(req)
            if req.msg_text.startswith('/test'):
                return self.test(req)

        state = self.app.get_state(req.user_id)
        if state.startswith('search'):
            return self.on_search(req)

        if state.startswith('study'):
            param = state.split(':')
            if len(param) > 1:
                if req.msg_text.startswith('/next'):
                    return self.on_study_unknown_end(req, word=param[1])
                else:
                    return self.on_study(req, word=param[1])

        if state.startswith('test'):
            return self.on_test(req)

        return self.help(req)

    def on_callback_query_dispatch(self, req: BloodyHellRequest):
        state = self.app.get_state(req.user_id)
        param = req.parameters

        if param[0] == 'navigate':
            if state.startswith('search'):
                return self.on_search_navigate(req, hash_key=param[1], index=int(param[2]))

        elif param[0] == 'more':
            if state.startswith('study'):
                return self.on_study_more(req, word=param[1])

        elif param[0] == 'translation':
            if state.startswith('study'):
                return self.on_study_translation(req, word=param[1])

        elif param[0] == 'select':
            if state.startswith('search'):
                return self.on_search_select(req, hash_key=param[1], index=int(param[2]))

        elif param[0] == 'known':
            return self.on_study_known(req, word=param[1])

        elif param[0] == 'unknown':
            return self.on_study_unknown(req, word=param[1])
