Set of modules to scrape Event Reports from the NRC.gov website. 

# Tests 

```bash
pytest 
```

# Usage
```python
    url = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2005/20050606en.html'

    e = EventNotificationReport.from_url(url, headers)

    url2 = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2017/20171129en.html'

    f = EventNotificationReport.from_url(url2, headers)

    url3 = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2005/20050607en.html'

    g = EventNotificationReport.from_url(url3, headers)

    g.events #>>> [event, event, ...]

    #categorical info
    g.events[0].eci.info
    #status info for power reactors
    g.events[0].esi
    #description info
    g.events[0].edi

    er_urls = generate_nrc_event_report_urls(2004,2019,only_known=False)

    from random import sample

    urls = sample(list(er_urls.values()), 10)

    # loop the urls and skip any 404s
    fetch_enrs(urls)


```
