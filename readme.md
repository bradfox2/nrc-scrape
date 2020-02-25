#Testing 

```bash
pytest test_main.py
```

#Usage
```python
    url = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2005/20050606en.html'

    e = EventNotificationReport.from_url(url, headers)

    url2 = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2017/20171129en.html'

    f = EventNotificationReport.from_url(url2, headers)

    url3 = 'https://www.nrc.gov/reading-rm/doc-collections/event-status/event/2005/20050607en.html'

    g = EventNotificationReport.from_url(url3, headers)

    er_urls = generate_nrc_event_report_urls()

    from random import sample

    urls = sample(list(er_urls.values()), 10)

    # loop the urls and skip any 404s
    fetch_enrs(urls)
```
