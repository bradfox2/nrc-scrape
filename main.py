from __future__ import annotations

import calendar
import typing
from typing import List

import requests
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError


def get_text_after_tag(segment, tag: str) -> List:
    return [x.next_sibling.strip() for x in segment.find_all(tag)]


def remove_inline_returns(text: str) -> str:
    return text.replace('\r', '').replace('\n', '').strip()


def get_text_without_tag(segment, tag: str) -> List:
    text = []
    text.append(segment.find(tag).previous_sibling.strip())
    text.extend(get_text_after_tag(segment, tag))
    return text


def chunks(l, n):
    # For item i in a range that is a length of l,
    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i+n]


url = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2005/20050606en.html'

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}

req = requests.get(url, headers=headers)

raw_html = BeautifulSoup(req.content, 'html.parser')

event_tables = raw_html.find(id='mainSubFull').find_all('table')[
    0].find_all('table')[2:]

event_info_table = event_tables[0]
tds = event_info_table.find_all('td')
event_type_text: List[str] = tds[0].text.strip()
event_number_text: List[str] = tds[1].text.strip()
event_contact_info: List[str] = get_text_after_tag(tds[2], 'br')
event_notification_timing: List[str] = get_text_after_tag(tds[3], 'br')
event_emergency_class_legal: List[str] = get_text_after_tag(tds[4], 'br')
event_contact_person: List[str] = remove_inline_returns(tds[5].text)

event_plant_status_table = event_tables[1]
unit_status_text = [x.text for x in event_plant_status_table.find_all('td')]
unit_table = zip(unit_status_text[:7], unit_status_text[7:])

event_description_table = event_tables[2].find('td')
event_text: List[str] = get_text_without_tag(event_description_table, 'br')
event_text: List[str] = list(
    filter(lambda x: x if x != '' else None, event_text))
event_title_text: str = event_text[0]


class EventNotificationReport(object):
    def __init__(self, raw_html):
        self.date = raw_html.find(id='mainSubFull').find_all('table')[
            0].find('h1').text
        self.raw_html = raw_html
        self._event_tables = self.raw_html.find(id='mainSubFull').find_all('table')[
            0].find_all('table')[2:]
        self._event_table_chunks = chunks(self._event_tables, 3)
        self.events: List[Events] = self._make_events()

    def _make_events(self):
        return [Event(chunk) for chunk in self._event_table_chunks]

    @classmethod
    def from_url(cls, url: str, headers) -> EventNotificationReport:
        req = None
        attempts = 0
        while req is None and attempts < 5:
            req = requests.get(url, timeout=5, headers=headers)
        req.raise_for_status()
        if not req:
            raise ValueError('Unable to fetch url')
        raw_html = BeautifulSoup(req.content, 'html.parser')
        return cls(raw_html)


class Event(object):

    ''' this is a dumb architecture and should be able to be handed the raw html of a section of the nrc page and parsed down from there, but oh well'''

    def __init__(self, table_chunks):
        self.table_chunks = table_chunks
        self.event_info: EventInfo = EventInfo(table_chunks[0])
        self.event_plant_status: EventPlantStatus = EventPlantStatus(
            table_chunks[1])
        self.event_description: List[str] = self.parse_description_text()
        self.event_description_title: str = self.event_description.pop(0)

    def parse_description_text(self) -> List[str]:
        event_description_table = self.table_chunks[2].find('td')
        event_text: List[str] = get_text_without_tag(
            event_description_table, 'br')
        event_text: List[str] = list(
            filter(lambda x: x if x != '' else None, event_text))
        return event_text


class EventTable(object):
    def __init__(self):
        pass


class EventInfo(EventTable):
    def __init__(self, first_table_chunk):
        super().__init__()
        self.event_info_table = first_table_chunk
        self.tds = self.event_info_table.find_all('td')
        self.event_type_text: List[str] = self.tds[0].text.strip()
        self.event_number_text: List[str] = self.tds[1].text.strip()
        self.event_contact_info: List[str] = get_text_after_tag(
            self.tds[2], 'br')
        self.event_notification_timing: List[str] = get_text_after_tag(
            self.tds[3], 'br')
        self.event_emergency_class_legal: List[str] = get_text_after_tag(
            self.tds[4], 'br')
        self.event_contact_person: List[str] = remove_inline_returns(
            self.tds[5].text)


class EventPlantStatus(EventTable):
    def __init__(self, second_table_chunk):
        super().__init__()
        self.event_plant_status_table = second_table_chunk
        self.unit_status_text = [
            x.text for x in self.event_plant_status_table.find_all('td')]
        self.unit_table = zip(
            self.unit_status_text[:7], self.unit_status_text[7:])


en = EventNotificationReport.from_url(url)


# get all dates
def build_nrc_event_report_url(year, month, day):
    month, day = str(month).zfill(2), str(day).zfill(2)
    url = f'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/{year}/{year}{month}{day}en.html'
    return url


assert build_nrc_event_report_url(
    2004, 12, 30) == 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2004/20041230en.html'

assert build_nrc_event_report_url(
    2004, 2, 3) == 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2004/20040203en.html'


def generate_nrc_event_report_urls():
    dates = {}
    for year in range(2003, 2020):
        # years before 2003 are in a weird format
        for month in range(1, 13):
            day_range = calendar.monthrange(year, month)
            for day in range(day_range[0], day_range[1]):
                dates[(year, month, day)] = build_nrc_event_report_url(
                    year, month, day)
    return dates


er_urls = generate_nrc_event_report_urls()

# 5592 days of event reports

urls = list(er_urls.values())[800:810]

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}

# loop the urls and skip any 404s
for url in urls:
    print(url)
    try:
        en = EventNotificationReport.from_url(url, headers)
    except HTTPError:
        next


# if __name__ == "__main__":
#     event_info_table = event_tables[0]
#     tds = event_info_table.find_all('td')
#     event_type_text: List[str] = tds[0].text.strip()
#     event_number_text: List[str] = tds[1].text.strip()
#     event_contact_info: List[str] = get_text_after_tag(tds[2], 'br')
#     event_notification_timing: List[str] = get_text_after_tag(tds[3], 'br')
#     event_emergency_class_legal: List[str] = get_text_after_tag(tds[4], 'br')
#     event_contact_person: List[str] = remove_inline_returns(tds[5].text)

#     event_plant_status_table = event_tables[1]
#     unit_status_text = [x.text for x in event_plant_status_table.find_all('td')]
#     unit_table = zip(unit_status_text[:7], unit_status_text[7:])

#     event_description_table = event_tables[2].find('td')
#     event_text:List[str] = get_text_without_tag(event_description_table,'br')
#     event_text:List[str] = list(filter(lambda x: x if x!='' else None, event_text))
#     event_title_text:str = event_text[0]
