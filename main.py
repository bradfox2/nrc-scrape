from __future__ import annotations

import calendar
import re
import typing
from typing import List

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from requests.exceptions import HTTPError


headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}


def get_text_after_tag(segment, tag: str) -> List:
    return [x.next_sibling.strip() for x in segment.find_all(tag) if x.next_sibling.strip() is not '']


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
    er_num_table_rows = er_tables_html.find_all(href = re.compile('#en'))
    return [int(x.text) for x in er_num_table_rows]

def event_categorical_info_html_from_demarc_tag(tag):
    # correct table appears to be 4 sibling away, and the first table that shows up
    return tag.find_next_siblings('table')[0]

def event_status_info_html_from_demarc_tag(tag):
    # correct table appears to be 4 sibling away, and the second table that shows up
    return tag.find_next_siblings('table')[1]

def event_desc_html_from_demarc_tag(tag):
    # correct table appears to be 4 sibling away, and the third table that shows up
    return tag.find_next_siblings('table')[2]

from abc import ABC, abstractmethod
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
        self.table_cols = self.table_html.find_all('td', {"align":"left"})
        self.info = {}
        self.emer_info = []
        self.person_info = []
        self.event_number = None
    
    def parse_table_html(self):
        #3x2 table, usually
        #1,1
        self.info['er_type'] = self._parse_er_type()
        #2,1 - rows delinated by <br> tags
        ei = []
        for segment in self.table_cols[1:4]: 
            ei.extend(get_text_without_tag(segment, 'br'))
        for text in ei:
            t = text.split(':',1)
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

            #store remaining fields 
            if len(t) > 1:
                k,v = t
                self.info[k] = v.strip()

        self.emer_info = self._parse_emergency_info(self.table_cols[4])
        self.person_info = self._parse_person_info(self.table_cols[5])
        self.event_number = int(self.info.get('Event Number', None).strip())   
        
    def _parse_er_type(self):
        return self.table_cols[0].text
    
    def _parse_cat_contact_info():
        pass
    
    def _parse_cat_time_info():
        pass
    
    def _parse_person_info(self, segment):
        return self._parse_stacked_line_breaks(segment)

    def _parse_emergency_info(sel,segment):
        emergency_class_text = [segment.find('br').previous_sibling.strip()]
        cfrs = ['10_cfr_sections',[]]
        for br in segment.find_all('br')[1:]:
            next_text = br.next_sibling
            if not (next_text and isinstance(next_text,NavigableString)):
                continue
            next_text2 = next_text.next_sibling
            if next_text2 and isinstance(next_text2, Tag) and next_text2.name == 'br':
                text = str(next_text).strip()
                if text:
                    cfrs[1].append(next_text.strip()) 
        return emergency_class_text + cfrs
    
    def _parse_stacked_line_breaks(self, segment):
        cfrs = [segment.find('br').previous_sibling.strip(),[]]
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
    
    def _check_and_get_geo_state_field(self, texts:List[str]):
        for idx, text in enumerate(texts):
            state_exist:int = text.find('\xa0State')
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

    def parse_table_html(self):

        header = self.table_rows[0]
        
        self.col_names = [col.text for col in header.find_all('td')]

        if len(self.col_names) == 0: return None
        
        # rows to list of dicts
        self.unit_table = [{self.col_names[idx]:col.text for idx, col in enumerate(row.find_all('td'))} for row in self.table_rows[1:]]

        return self.unit_table

class EventDescInfo(EventInfo):
    def __init__(self, table_html):
        super().__init__(table_html)
    
    def parse_table_html(self):
        return get_text_without_tag(self.table_html, 'br')

def get_event_html_tables_from_main(main_table):
    # tables appear to have a name that follows <a name="en{eventnumber}"></a>
    er_demarcation_tags = main_table[0].find_all('a', {"name":re.compile('en')})
    event_tables_html = []

    for tag in er_demarcation_tags:
        
        event_info_html = event_categorical_info_html_from_demarc_tag(tag)
        eci = EventCategoricalInfo(event_info_html)
        
        event_status_html = event_status_info_html_from_demarc_tag(tag)
        esi = EventStatusInfo(event_status_html)
        
        event_desc_html = event_desc_html_from_demarc_tag(tag)
        edi = EventDescInfo(event_desc_html)

        event_tables_html.append([eci, esi, edi])

    return event_tables_html

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

# get all dates
def build_nrc_event_report_url(year, month, day):
    month, day = str(month).zfill(2), str(day).zfill(2)
    url = f'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/{year}/{year}{month}{day}en.html'
    return url

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

if __name__ == "__main__":
    
    url = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2005/20050606en.html'

    assert build_nrc_event_report_url(
        2004, 12, 30) == 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2004/20041230en.html'

    assert build_nrc_event_report_url(
        2004, 2, 3) == 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2004/20040203en.html'

    req = requests.get(url, headers=headers)
    page_html = BeautifulSoup(req.content, 'html.parser')
    main_table = get_main_table(page_html)
    event_html_tables = get_event_html_tables_from_main(main_table)
    
    ex_cat_info_table = event_html_tables[0][2]
    ex_cat_info_table.parse_table_html()
    #ex_cat_info_table.info
    #ex_cat_info_table.person_info
    

    # er_urls = generate_nrc_event_report_urls()

    # 5592 days of event reports

#    urls = list(er_urls.values())[800:810]

 #   headers = {
        #'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}

    # loop the urls and skip any 404s
 #   for url in urls:
 #       print(url)
 #       try:
 #           en = EventNotificationReport.from_url(url, headers)
  #      except HTTPError:
  #          next


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



