#!/usr/bin/env python3

import os
import sys
import json
import requests, bs4
import re
from collections import namedtuple

ANKICONNECT_ADDRESS = 'http://localhost:8765'

try:
    ANKICONNECT_ADDRESS = os.environ['ANKICONNECT_ADDRESS']
except KeyError:
    pass

LangPair = namedtuple('LangPair', ['jp', 'en'])

_re_kanji = re.compile(r'[\u3400-\u4DB5\u4E00-\u9FCB\uF900-\uFA6A]')

def _uniqify(a):
    """ Remove duplicate elements from an array. """
    seen = {}
    result = []
    for x in a:
        if x in seen: continue
        result.append(x)
        seen[x] = 1
    return result

def _ac_request_text(action, params):
    """ Generate JSON text used in an AnkiConnect POST request. """
    return json.dumps({ 'action': action, 'version': 6, 'params': params })

def ac_check():
    """ Checks for an active connection to AnkiConnect.  """
    res = requests.get(ANKICONNECT_ADDRESS)
    if res.status_code != 200:
        print('Error connecting to AnkiConnect: {}'.format(res.status_code), file=sys.stderr)
        return False
    return True

def ac_request(action, params):
    """ Send a request to AnkiConnect and return the result. """
    message = _ac_request_text(action, params)
    res = requests.post(ANKICONNECT_ADDRESS, message)
    if res.status_code != 200:
        print('AnkiConnect error {}: {}'.format(res.status_code, res.json()))
    return json.loads(res.text)

def anki_construct_field(arr):
    """ Print elements of an array, each separated by a newline, with no trailing space. """
    if len(arr) == 0: return ""
    f = arr[0]
    for x in arr[1:]:
        f += "\n" + x
    return f

def jisho_sentences(word, count=20):
    """ Query Jisho.org for example sentences for a word. """
    sentences = []

    page = 1
    while page * 20 <= count:
        res = requests.get('https://jisho.org/search/{} %23sentences?page={}'.format(word, page))

        if res.status_code != 200:
            print('Error loading sentences from Jisho: {}.'.format(res.status_code), file=sys.stderr)
            return sentences

        soup = bs4.BeautifulSoup(res.text, 'html.parser')

        for sentence_content in soup.find_all('div', {'class': 'sentence_content'}):
            sentence_jp = sentence_content.find('ul', {'class': 'japanese_sentence'})
            for furigana in sentence_jp.find_all('span', {'class': 'furigana'}):
                furigana.decompose()
            sentence_en = sentence_content.find('div', {'class': 'english_sentence'}).find('span', {'class': 'english'})
            sentences.append(LangPair(sentence_jp.text.strip(), sentence_en.text.strip()))

            if len(sentences) == count: return sentences

        # Check if we have exhausted all of Jisho's sentences.
        if page * 20 > count and not len(sentences) > count: return sentences

        page += 1

    return sentences

def jisho_kanji_keywords(kanji):
    """ Query Jisho.org for keywords for a kanji. """
    if _re_kanji.match(kanji) == None:
        raise ValueError('argument must be a kanji character')

    res = requests.get('https://jisho.org/search/{} %23kanji'.format(kanji))
    if res.status_code != 200:
        print('Error loading kanji keywords from Jisho: {}.'.format(res.status_code), file=sys.stderr)
        return None

    soup = bs4.BeautifulSoup(res.text, 'html.parser')
    return soup.find('div', {'class': 'kanji-details__main-meanings'}).text.strip()

def jisho_dictionary_entry(word):
    """ Query Jisho.org for a dictionary entry for a word. """
    res = requests.get('https://jisho.org/api/v1/search/words?keyword={}'.format(word))
    if res.status_code != 200:
        print('Error loading dictionary entry from Jisho: {}.'.format(res.status_code), file=sys.stderr)
        return None
    return json.loads(res.text)

def kanji_from_word(word):
    """ Get a list of unique kanji from a string. """
    return _uniqify(_re_kanji.findall(word))
