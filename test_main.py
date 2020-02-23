import main
from main import build_nrc_event_report_url, generate_nrc_event_report_urls, EventNotificationReport

import calendar
import re
import typing
from typing import List

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from requests.exceptions import HTTPError

import pytest

urls = ['https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2005/20050606en.html', 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2017/20171129en.html']

@pytest.fixture
def headers():
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}
    return headers

def test_build_nrc_event_report_url():
    assert build_nrc_event_report_url(
        2004, 12, 30) == 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2004/20041230en.html'

    assert build_nrc_event_report_url(
        2004, 2, 3) == 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2004/20040203en.html'

@pytest.mark.parametrize('url', urls)
def test_event_notification_report_whole(url, headers):
    e = EventNotificationReport.from_url(url, headers)
    assert isinstance(e, EventNotificationReport)

def test_event_notification_report_class_2(headers):
    url2 ='https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2017/20171129en.html'

    f = EventNotificationReport.from_url(url2, headers)
    assert len(f.events) == 4
    assert str(f) == "Event Notification Report from 2017-11-29. 4 events, numbers 53079, 53080, 53082, 53095."

def test_generate_er_urls():
    len(generate_nrc_event_report_urls(2003, 2019)) == 5263

