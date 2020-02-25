import main
from main import BeautifulSoup
import requests
from main import headers

def get_events_toc_html():
    req = requests.get('https://www.nrc.gov/reading-rm/doc-collections/event-status/event/', headers=headers)
    return req.content


def get_main_sub(page_html):
    return page_html.find(id='mainSub')

def get_links_from_year_para(year_para):
    return year_para.find_all('a')

#todo cache this
def get_nrc_url(url):
    req=None
    attempts = 0
    while req is None and attempts < 5:
        req = requests.get(url, timeout=5, headers=headers)
    req.raise_for_status()
    if not req:
        raise ValueError('Unable to fetch url')
    return req

def get_year_urls(year_paras):
    links = []
    for year_para in year_paras:
        year_links = get_links_from_year_para(year_para)
        for year_link in year_links:
            url = f'http://www.nrc.gov{year_link.get("href")}'
            links.append(url)
    return links

def get_tag_name_property(tag, name):
    return tag.attrs(name)


def make_urls():
    events_html=get_events_toc_html()
    page_html = BeautifulSoup(events_html, 'html.parser')
    year_paras = get_main_sub(page_html).find_all_next('p')[1:4]
    yurls = get_year_urls(year_paras)

    all_links = {}

    for yurl in yurls:
        year_links = []

        page_html = get_nrc_url(yurl).content
        parsed = BeautifulSoup(page_html,'html.parser')
        main_sub = get_main_sub(parsed)

        #month listing is first paragraph in main sub
        months = main_sub.find_next('p')

        #get month anchor links
        months = months.find_all('a')

        #get the month name from anchor link definition
        months = [month.get('href')[1:] for month in months]

        #get month name that have a url for this year 
        months_with_url = [x.find('a') for x in main_sub.find_all('h3') if x.find('a').attrs.get('name') in months]

        #months broken up by h3 tags
        month_h3s = main_sub.find_all('h3')

        # filter h3s to just our months listed
        for month in month_h3s:
            if month.find('a') in months_with_url:
                # next p tag holds the links
                print(yurl)
                try:
                    #todo 2017 and older will not parse all dates, need to investigate
                    year_links.append([yurl + enr_url.get('href') for enr_url in month.find_next('p').find_all('a')])
                except:
                    Warning(f'No {yurl}')
        # year is end of link
        year_num = yurl[-5:-1]
        all_links[year_num] = year_links

    return all_links

if __name__ == "__main__":
    url_maker()

