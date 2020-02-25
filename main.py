from __future__ import annotations

import calendar
import datetime
import pprint
import re
import sys
import typing
from abc import ABC, abstractmethod
from typing import List

import dateutil.parser as dp
import dateutil.tz as tz
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from requests.exceptions import HTTPError

import logging
import logs_setup

# use webbrowser headers to stop nrc security stuff from killing our requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}


def get_text_after_tag(segment, tag: str) -> List:
    texts = []
    for x in segment.find_all(tag):
        if x.next_sibling is not None and isinstance(x.next_sibling,str):
            if x.next_sibling.strip() not in ('', None):
                texts.append(x.next_sibling.strip())
        elif str(x)[:4] == '<br>' and str(x)[:4] != '<br><br>':
            texts.append(x.text.strip())
    return texts
    #return [x.next_sibling.strip() for x in segment.find_all(tag) if x.next_sibling.strip() not in  ('', None)]


def remove_inline_returns(text: str) -> str:
    return text.replace('\r', '').replace('\n', '').strip()


def get_text_without_tag(segment, tag: str) -> List:
    text = []
    t = segment.find(tag)
    if t is None:
        return [segment.text]
    text.append(t.previous_sibling.strip())
    text.extend(get_text_after_tag(segment, tag))
    return text


def chunks(l, n):
    # For item i in a range that is a length of l,
    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i+n]


def get_main_table(page_html):
    return page_html.find(id='mainSubFull').find_all('table')


def split_main_sub_2_tables(page_html):
    return page_html.find(id='mainSubFull').find_all('table')[
        0].find_all('table')


def get_event_report_numbers(er_tables_html):
    er_num_table_rows = er_tables_html.find_all(href=re.compile('#en'))
    return [int(x.text) for x in er_num_table_rows if x != None]


def event_html_from_demarc_tag(tag, table_num):
    ''' Gets the table_num'th html table tag after tag.
    Primarily used to get the html table under the event demarcation tag. 
    '''
    return tag.find_next_siblings('table')[table_num]


class EventInfo(ABC):
    def __init__(self, table_html):
        self.table_html = table_html

    def __repr__(self):
        return self.table_html.prettify()

    @abstractmethod
    def parse_table_html(self):
        pass


class EventCategoricalInfo(EventInfo):
    def __init__(self, table_html):
        super().__init__(table_html)
        self.table_cols = self.table_html.find_all('td', {"align": "left"})
        self.info = {}
        self.emer_info = []
        self.person_info = []
        self.event_number = None
        self.parse_table_html()

    def __repr__(self):
        pp = pprint.PrettyPrinter()
        return str(pp.pprint(self.info))

    def parse_table_html(self):
        # 3x2 table, usually
        # 1,1
        self.info['er_type'] = self._parse_er_type()
        # 2,1 - rows delinated by <br> tags
        ei = []
        for segment in self.table_cols[1:4]:
            ei.extend(get_text_without_tag(segment, 'br'))
        for text in ei:
            t = text.split(':', 1)
            if t[0] in {'Region', 'City'}:

                # NRC has put some colon seperated fields in line or
                # seperated by line break into a table row, need to
                # parse the row and seperate the 2nd colon seperated
                # field from the first

                # check for the state field in the Region or City rows
                self._check_and_get_geo_state_field(t)

                # If a 2nd field is found (e.g. state) add it back to
                # string data list for processing and then remove from
                # current colon sep value dict value, 2nd col sep field is
                # still a 'something: value' string, and so it is the last
                # item on list
                ei.append(t[-1])
                t.pop()

            # store remaining fields
            if len(t) > 1:
                k, v = t
                self.info[k.strip()] = v.strip()

        self.emer_info = self._parse_emergency_info(self.table_cols[4])
        self.person_info = self._parse_person_info(self.table_cols[5])
        self.event_number = int(self.info.get('Event Number', None))
        self.event_date = dp.parse(self.info.get(
            'Event Date', None), fuzzy=True).date()
        self.event_time = self._parse_time(self.info.get('Event Time', None))
        self.facility = self._get_from_self_info('Facility')
        self.hq_ops_officer = self._get_from_self_info('HQ OPS Officer')
        self.last_update_date = dp.parse(
            self._get_from_self_info('Last Update Date'), fuzzy=True).date()
        self.nrc_notified_by = self._get_from_self_info('NRC Notified By')
        self.notification_date = dp.parse(
            self._get_from_self_info('Notification Date'), fuzzy=True).date()
        self.notification_time = self._parse_time(
            self._get_from_self_info('Notification Time'))
        self.rx_type = self._get_from_self_info('RX Type')
        self.region = self._get_from_self_info('Region')
        self.state = self._get_from_self_info('State')
        self.unit = self._get_from_self_info('Unit')
        self.er_type = self._get_from_self_info('er_type')
        self.licensee = self._get_from_self_info('Licensee')
        self.city = self._get_from_self_info('City')
        self.county = self._get_from_self_info('County')
        self.rep_org = self._get_from_self_info('Rep Org')

    def _parse_date(self, date_string):
        try:
            dte = dp.parse(date_string, fuzzy=True).date()
            return dte
        except ValueError:
            Warning(f'Unable to parse {date_string} into datetime object.')
            return date_string

    def _parse_time(self, time_string):

        tzinfos = {"EST": tz.gettz('EST'), "EDT": tz.gettz('EST'), "ET": tz.gettz('EST'), 'PDT': tz.gettz('America/Los_Angeles'), 'CST': tz.gettz('America/Chicago'),
                   'CDT': tz.gettz('America/Chicago'), 'MDT': tz.gettz('America/Denver'), "PST": tz.gettz('America/Los_Angeles'), "MST": tz.gettz('America/Denver')}

        try:
            dte = dp.parse(time_string, fuzzy=True, tzinfos=tzinfos).time()
            return dte
        except ValueError:
            Warning(f'Unable to parse {time_string} into datetime object.')
            return time_string

    def _get_from_self_info(self, field):
        return self.info.get(field, None)

    def _parse_er_type(self):
        return self.table_cols[0].text

    def _parse_person_info(self, segment):
        return self._parse_stacked_line_breaks(segment)

    def _parse_emergency_info(self, segment):
        emergency_class_text = [segment.find('br').previous_sibling.strip()]
        cfrs = ['10_cfr_sections', []]
        for br in segment.find_all('br')[1:]:
            next_text = br.next_sibling
            if not (next_text and isinstance(next_text, NavigableString)):
                continue
            next_text2 = next_text.next_sibling
            if next_text2 and isinstance(next_text2, Tag) and next_text2.name == 'br':
                text = str(next_text).strip()
                if text:
                    cfrs[1].append(next_text.strip())
        return emergency_class_text + cfrs

    def _parse_stacked_line_breaks(self, segment):
        cfrs = [segment.find('br').previous_sibling.strip(), []]
        for br in segment.find_all('br'):
            next_text = br.next_sibling
            if not (next_text and isinstance(next_text, NavigableString)):
                continue
            next_text2 = next_text.next_sibling
            if next_text2 and isinstance(next_text2, Tag) and next_text2.name == 'br':
                text = str(next_text).strip()
                if text:
                    cfrs[1].append(next_text.strip())
        return cfrs

    def _check_and_get_geo_state_field(self, texts: List[str]):
        for _, text in enumerate(texts):
            state_exist: int = text.find('\xa0State')
            if state_exist != -1:
                texts.remove(text)
                prev_val, state_kv = text.split('\xa0')
                texts.append(prev_val)
                texts.append(state_kv)


class EventStatusInfo(EventInfo):
    def __init__(self, table_html):
        super().__init__(table_html)
        self.unit_status_text = None
        self.unit_table = None
        self.table_cols = self.table_html.find_all('td')
        self.table_rows = self.table_html.find_all('tr')
        self.info = self.parse_table_html()
    
    def __repr__(self):
        return str(self.unit_table)

    def parse_table_html(self):

        header = self.table_rows[0]

        self.col_names = [col.text for col in header.find_all('td')]

        if len(self.col_names) == 0:
            return None

        # rows to list of dicts
        self.unit_table = [{self.col_names[idx]:col.text for idx, col in enumerate(
            row.find_all('td'))} for row in self.table_rows[1:]]

        return self.unit_table


class EventDescInfo(EventInfo):
    def __init__(self, table_html):
        super().__init__(table_html)
        self.info = self.parse_table_html()

    def __repr__(self):
        return str(self.info)

    def parse_table_html(self):
        return get_text_without_tag(self.table_html, 'br')


class Event(object):
    def __init__(self, demarcation_tag):

        self._event_info_html = event_html_from_demarc_tag(
            demarcation_tag, 0)
        self.eci = EventCategoricalInfo(self._event_info_html)

        # non power reactors dont have status'
        if self.eci.er_type == 'Power Reactor':
            self._event_status_html = event_html_from_demarc_tag(
                demarcation_tag, 1)
            self.esi = EventStatusInfo(self._event_status_html)
            self._event_desc_html = event_html_from_demarc_tag(
                demarcation_tag, 2)
            self.edi = EventDescInfo(self._event_desc_html)

        else:
            self.esi = None
            self._event_desc_html = event_html_from_demarc_tag(
                demarcation_tag, 1)
            self.edi = EventDescInfo(self._event_desc_html)
            
            # if nrc has added another section about material event cat, reparse the full desc table
            if 'This material event contains' in self.edi.info[0].strip():
                self._event_desc_html = event_html_from_demarc_tag(demarcation_tag, 2)
                self.edi = EventDescInfo(self._event_desc_html)

        self.event_number = self.eci.event_number

    def __repr__(self):
        return f'Event Num: {self.event_number}'


class EventNotificationReport(object):
    def __init__(self, page_html):
        self.date = dp.parse(page_html.find(id='mainSubFull').find_all('table')[
            0].find('h1').text, fuzzy=True)
        self.main_table = self.get_main_table(page_html)
        self.events = self.get_events_from_main(self.main_table)
        self._page_html = page_html
        self.num_events = len(self.events)

    def __repr__(self):
        return f'Event Notification Report from {str(self.date.date())}. {self.num_events} events, numbers {", ".join([str(x.event_number) for x in self.events])}.'

    def get_main_table(self, page_html):
        return page_html.find(id='mainSubFull').find_all('table')

    @classmethod
    def get_events_from_main(cls, main_table):
        # tables appear to have a name that follows <a name="en{eventnumber}"></a>
        er_demarcation_tags = main_table[0].find_all(
            'a', {"name": re.compile('en')})
        event_tables_html = []

        for tag in er_demarcation_tags:
            e = Event(tag)
            event_tables_html.append(e)
        return event_tables_html

    @classmethod
    def from_url(cls, url: str, headers) -> EventNotificationReport:
        req = None
        attempts = 0
        while req is None and attempts < 5:
            req = requests.get(url, timeout=5, headers=headers)
        req.raise_for_status()
        if not req:
            raise ValueError('Unable to fetch url')
        page_html = BeautifulSoup(req.content, 'html.parser')
        return cls(page_html)


# get all dates
def build_nrc_event_report_url(year, month, day):
    month, day = str(month).zfill(2), str(day).zfill(2)
    url = f'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/{year}/{year}{month}{day}en.html'
    return url
    

import url_maker

def generate_nrc_event_report_urls(start_year=2004, end_year=datetime.date.today().year, only_known=False):
    ''' construct a list of nrc event report page urls from year start to years end'''

    if only_known is True:
        urll = []
        urls = url_maker.make_urls()
        for key in urls.keys():
            urll.extend(urls[key])
        return urll    

    dates = {}
    for year in range(start_year, end_year):
        # years before 2003 are in a weird format
        for month in range(1, 13):
            day_range = calendar.monthrange(year, month)
            for day in range(day_range[0], day_range[1]):
                dates[(year, month, day)] = build_nrc_event_report_url(
                    year, month, day)
    return dates


def fetch_enrs(urls):
    '''generates a list of EventNotificationReport objects from a list of urls'''

    error_list = []
    enrs = []
    four_oh_fours = []
    nurls = len(urls)
    for idx, url in enumerate(urls):
        print(f'{idx}/{nurls}, {url}')
        try:
            en = EventNotificationReport.from_url(url, headers)
            enrs.append(en)
            sl.info(en)
        except HTTPError:
            four_oh_fours.append(url)
            fl.info(url)
            next
        except:
            error_list.append((url, sys.exc_info()[0]))
            el.info((url, sys.exc_info()[0]))
            print('ERROR!')
            next
    
    print(f'{len(enrs)}:OK, {len(error_list)}:Failed, {len(four_oh_fours)}:404s')

if __name__ == "__main__":

    url = 'http://www.nrc.gov/reading-rm/doc-collections/event-status/event/2019/20190517en.html'

    e = EventNotificationReport.from_url(url, headers)

    url3 = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2018/20181112en.html'

    h = EventNotificationReport.from_url(url3, headers)

    er_urls = generate_nrc_event_report_urls()

    from random import sample

    urls = sample(list(er_urls.values()), 10)

    # loop the urls and skip any 404s

    fetch_enrs(urls)

    sl = logging.getLogger('success_log')
    el = logging.getLogger('error_log')
    fl = logging.getLogger('fof_log')

    fetch_enrs(urls)
