import main
from main import build_nrc_event_report_url, generate_nrc_event_report_urls, EventNotificationReport, get_text_after_tag, get_text_without_tag

import calendar
import re
import typing
from typing import List

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from requests.exceptions import HTTPError

import pytest

urls = ['https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2005/20050606en.html',
        'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2017/20171129en.html', 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2019/20190517en.html']


@pytest.fixture
def headers():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}
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
    url2 = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2017/20171129en.html'

    f = EventNotificationReport.from_url(url2, headers)
    assert len(f.events) == 4
    assert str(
        f) == "Event Notification Report from 2017-11-29. 4 events, numbers 53079, 53080, 53082, 53095."


def test_generate_er_urls():
    len(generate_nrc_event_report_urls(2003, 2019)) == 5263


def test_get_text_without_tag():
    # make sure we can parse double br tags as in 
    # <html>
    # <br>
    # <br>
    # text 
    # <br>
    # <br>
    html = """<table border="1" cellpadding="3" cellspacing="0" width="98%">
                <tr>
                <td align="left" scope="row"> CONTROL ROOM ENVELOPE INOPERABLE DUE TO DOOR HANDLE DETACHING<br><br>"On April 11, 2019, at 0200 CDT the shift operating crew declared the control room envelope inoperable in accordance with Technical Specification (TS) 3.7.6.1 due to the door handle for Door 86 (H&amp;V Airlock Access Door) being detached. Operations entered TS 3.7.6.1 action b, which requires that with one or more control room emergency air filtration trains inoperable due to inoperable control room envelope boundary in MODES 1, 2, 3, or 4, then: 1. Immediately initiate action to implement mitigating actions; 2. Within 24 hours, verify mitigating actions ensure control room envelope occupant exposures to radiological, chemical, and smoke hazards will not exceed limits; and 3. Within 90 days, restore the control room envelope boundary to OPERABLE status.  Action b.1 was completed by sealing the hole in Door 86 at 0232 CDT.  This event is reportable pursuant to 10 CFR 50.72(b)(3)(v)(D), 'event or condition that could have prevented fulfilment of a safety function of structures or systems that are needed to (D) mitigate the consequences of an accident,' due to the control room envelope being inoperable.  <br><br>"The licensee notified the NRC Resident."<br><br>* * * RETRACTION ON 5/17/19 AT 1620 EDT FROM MARIA ZAMBER TO BETHANY CECERE * * *<br><br>"This is a Non-Emergency Notification from Waterford 3. This is a retraction of EN 53991. This event was evaluated in accordance with the corrective action process. The original operability determination of inoperable was made based on a conservative evaluation that with the door handle for Door 86 (Heating and Ventilation Airlock Access Door) being detached, the control room envelope boundary could not perform its safety function. A more detailed engineering evaluation was subsequently performed. This shows that the condition of the door handle being detached is bounded by the most recently performed non-pressurized radiological tracer gas test, as the control room envelope differential pressure was maintained more positive with the detached door handle as compared to that observed during the test. Additionally, the control room envelope differential pressure trends showed no discernable change between the two conditions of the door handle detached or with the opening taped over (resulting in an air tight seal). This information supports the conclusion that with the door handle for Door 86 being detached, the control room envelope boundary remained operable and did not constitute a condition that could have prevented fulfillment of a safety function of structures or systems that are needed to mitigate the consequences of an accident; therefore, this event is not reportable per 10 CFR 50.72(b)(3)(v)(D).<br><br>"The licensee notified the NRC Resident Inspector."<br><br>Notified R4DO (Proulx). </br></br></br></br></br></br></br></br></br></br></br></br></td>
                </tr>
                </table>"""

    html = BeautifulSoup(html, 'html.parser')

    assert get_text_without_tag(html, 'br') == ['CONTROL ROOM ENVELOPE INOPERABLE DUE TO DOOR HANDLE DETACHING', '"On April 11, 2019, at 0200 CDT the shift operating crew declared the control room envelope inoperable in accordance with Technical Specification (TS) 3.7.6.1 due to the door handle for Door 86 (H&V Airlock Access Door) being detached. Operations entered TS 3.7.6.1 action b, which requires that with one or more control room emergency air filtration trains inoperable due to inoperable control room envelope boundary in MODES 1, 2, 3, or 4, then: 1. Immediately initiate action to implement mitigating actions; 2. Within 24 hours, verify mitigating actions ensure control room envelope occupant exposures to radiological, chemical, and smoke hazards will not exceed limits; and 3. Within 90 days, restore the control room envelope boundary to OPERABLE status.  Action b.1 was completed by sealing the hole in Door 86 at 0232 CDT.  This event is reportable pursuant to 10 CFR 50.72(b)(3)(v)(D), \'event or condition that could have prevented fulfilment of a safety function of structures or systems that are needed to (D) mitigate the consequences of an accident,\' due to the control room envelope being inoperable.', '"The licensee notified the NRC Resident."', '* * * RETRACTION ON 5/17/19 AT 1620 EDT FROM MARIA ZAMBER TO BETHANY CECERE * * *', '"This is a Non-Emergency Notification from Waterford 3. This is a retraction of EN 53991. This event was evaluated in accordance with the corrective action process. The original operability determination of inoperable was made based on a conservative evaluation that with the door handle for Door 86 (Heating and Ventilation Airlock Access Door) being detached, the control room envelope boundary could not perform its safety function. A more detailed engineering evaluation was subsequently performed. This shows that the condition of the door handle being detached is bounded by the most recently performed non-pressurized radiological tracer gas test, as the control room envelope differential pressure was maintained more positive with the detached door handle as compared to that observed during the test. Additionally, the control room envelope differential pressure trends showed no discernable change between the two conditions of the door handle detached or with the opening taped over (resulting in an air tight seal). This information supports the conclusion that with the door handle for Door 86 being detached, the control room envelope boundary remained operable and did not constitute a condition that could have prevented fulfillment of a safety function of structures or systems that are needed to mitigate the consequences of an accident; therefore, this event is not reportable per 10 CFR 50.72(b)(3)(v)(D).', '"The licensee notified the NRC Resident Inspector."', 'Notified R4DO (Proulx).']
