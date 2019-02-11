import re
import math
import nltk
import nltk.data
import collections
from typing import List, Tuple
from nltk.stem import WordNetLemmatizer, SnowballStemmer


class NLPHelper:

    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stemmer = SnowballStemmer('english')
        self.tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

    def get_stem(self, word):
        for pos in ['a', 'n', 'v']:
            word = self.lemmatizer.lemmatize(word, pos)

        return self.stemmer.stem(word)

    def get_tokens(self, sentence):
        tokens = [
            token
            for token in nltk.wordpunct_tokenize(sentence)
            if token.isalpha() and len(token) > 2
        ]
        return tokens

    def split_text(self, text) -> List[Tuple[str, str, float]]:
        ne_stems = set()
        word_map = collections.defaultdict(list)

        text = re.sub('n\'[ts]', '', text)
        sentences = self.tokenizer.tokenize(text)

        for sentence in sentences:
            tokens = self.get_tokens(sentence)
            for i in range(len(tokens)):
                token = tokens[i].lower()
                stem = self.get_stem(token)

                if i == 0 or tokens[i][0].islower():
                    word_map[stem].append(token)
                else:
                    ne_stems.add(stem)

        scored_words = []
        for stem, words in word_map.items():
            if stem not in ne_stems:
                word = min(words, key=len)  # type: str
                if len(word) > 2:
                    freq = len(words) / math.log(len(word))
                    scored_words.append((word, stem, freq))

        return scored_words
