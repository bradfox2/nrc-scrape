from __future__ import annotations

import calendar
import re
import typing
from typing import List

import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

import main
from main import get_event_html_tables_from_main, get_main_table

from pytest import fixture

url = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2005/20050606en.html'

@fixture
def url():
    return url

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}

@fixture
def page_html(url):
    req = requests.get(url, headers=headers)
    page_html = BeautifulSoup(req.content, 'html.parser')
    return page_html
    
def test_main_table(page_html):
    return get_main_table(page_html)

def test_event_html_tables():
    pass

main_sub_table = test_main_table()

event_html_tables = get_event_html_tables_from_main(main_sub_table)

ex_cat_info_table = event_html_tables[0][0]

ex_cat_info_table.parse_table_html()

ex_cat_info_table.parsed_data
