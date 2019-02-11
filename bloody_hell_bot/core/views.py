import random
from telepot.namedtuple import InlineKeyboardMarkup, ReplyKeyboardMarkup

from bloody_hell_bot.dictionaries.dictionary import DefinitionType


def start():
    return (
        'Hi and welcome! I\'m gonna make you watch your favourite movies in english with pleasure.'
    )


def help():
    return (
        'In search mode (default) write any movie title (for series use S1E2 format);\n'
        '/study - start learning words, imported from subtitles;\n'
        '/test - start testing words, studied before;\n'
        '/end - finish current operation, return to search mode.\n'
    )


def initialize(count):
    return (
        'I\'ve created your initial vocabulary (%d) from russian cognates, functionals and most frequent words.'
        '' % count
    )


def study_notfound(word):
    return (
        'Sorry, cannot find a definition for "%s".'
        '\nTry @pic or external dictionary.'
        '\nGo to the /next word.'
        '' % word
    )


def search_import(count):
    if count > 0:
        return '%d new words to /study!' % count
    else:
        return 'You already know it!'


def navigate_markup(length, key, index, ok=True):
    buttons = []
    if length > 1:
        buttons.append(dict(text='←', callback_data='navigate_%s_%d' % (key, (index - 1) % length)))
    if ok:
        buttons.append(dict(text='ok', callback_data='select_%s_%d' % (key, index % length)))
    if length > 1:
        buttons.append(dict(text='→', callback_data='navigate_%s_%d' % (key, (index + 1) % length)))

    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None


def known_unknown_markup(word):
    return InlineKeyboardMarkup(inline_keyboard=[[
        dict(text='known', callback_data='known_%s' % word),
        dict(text='unknown', callback_data='unknown_%s' % word)
    ]])


def study_more_markup(word):
    return InlineKeyboardMarkup(inline_keyboard=[[
        dict(text='more', callback_data='more_%s' % word),
        dict(text='i give up', callback_data='translation_%s' % word)
    ]])


def answers_markup(answers):
    rows = []
    answers = sorted(answers)
    full_rows_count = len(answers) // 2

    for i in range(full_rows_count):
        rows.append([answers[2*i], answers[2*i+1]])

    if len(answers) > 2 * full_rows_count:
        rows.append([answers[-1]])

    return ReplyKeyboardMarkup(keyboard=rows, one_time_keyboard=True, resize_keyboard=True)


def study_cards(card: dict, limit=5) -> list:
    views = []

    view = '<b>%s</b>' % (card['word'].capitalize())
    if card.get(DefinitionType.PRONUNCIATION):
        view += ' [%s]' % (card[DefinitionType.PRONUNCIATION])
    if card.get(DefinitionType.SYNONIM):
        view += '\n%s' % (', '.join(card[DefinitionType.SYNONIM][:limit]))
    views.append(view)

    for meaning in card.get(DefinitionType.MEANING, [])[:limit]:
        views.append(meaning)

    if card.get(DefinitionType.EXAMPLE):
        views.append('<i>%s</i>' % card[DefinitionType.EXAMPLE][0])

    return views


def test(data):
    view = '%s' % data['title']
    view += '\n<i>%s</i>' % data['question']
    return view


def test_mark(correct):
    correct_var = ['Good!', 'That\'s right!', 'Nice.', 'Absolutely!', 'Yeah!', 'Damn right.']
    incorrect_var = ['Oh no.', 'Next time.', 'Common!', 'Pull yourself together!']

    if correct:
        return random.choice(correct_var)
    else:
        return random.choice(incorrect_var)
