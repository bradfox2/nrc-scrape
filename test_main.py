import main
from __future__ import annotations

import calendar
import re
import typing
from typing import List

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from requests.exceptions import HTTPError

url = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2005/20050606en.html'

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}

req = requests.get(url, headers=headers)

page_html = BeautifulSoup(req.content, 'html.parser')

print(page_html.prettify())


#event contact tables

event_html_tables = get_event_html_tables_from_main(main_sub_table)

ex_cat_info_table = event_html_tables[0][0]

ex_cat_info_table.parse_table_html()

ex_cat_info_table.table_cells

ex_cat_info_table.event_contact_and_time

ex_cat_info_table.emer_info

ex_cat_info_table.person_info