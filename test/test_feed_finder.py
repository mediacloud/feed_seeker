import time

import pytest
import responses

from feed_seeker import feed_seeker


def test__is_feed_url():
    assert not feed_seeker._is_feed_url('nytimes.com')
    assert feed_seeker._is_feed_url('nytimes.rss')
    assert not feed_seeker._is_feed_url('rssnews.com')


def test__might_be_feed_url():
    assert not feed_seeker._might_be_feed_url('nytimes.com')
    assert feed_seeker._might_be_feed_url('nytimes.rss')
    assert feed_seeker._might_be_feed_url('rssnews.com')


@responses.activate
def test_find_feed_max_time():
    max_time = 0.5

    def request_callback(request):
        time.sleep(2 * max_time)
        return (200, {}, '')

    url = 'http://nopenopenope.nope'
    responses.add_callback(responses.GET, url, callback=request_callback)

    # Make sure it can raise
    with pytest.raises(TimeoutError):
        feed_seeker.find_feed_url(url, max_time=max_time)

    def request_callback(request):
        return (200, {}, '')

    # make sure it doesn't always raise
    url = 'http://yupyupyup.yup'
    responses.add_callback(responses.GET, url, callback=request_callback)
    feed_seeker.find_feed_url(url, max_time=max_time)


def test_feeedly_feeds():
    url = 'https://www.nytimes.com'
    feeds_gen = feed_seeker.find_feedly_feeds(url)
    feeds_list = list(feeds_gen)
    some_expected_feeds = [
        'http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml',
        'http://www.nytimes.com/services/xml/rss/nyt/World.xml',
        'http://www.nytimes.com/services/xml/rss/nyt/US.xml',
        'http://www.nytimes.com/services/xml/rss/nyt/Sports.xml',
    ]
    for feed in some_expected_feeds:
        assert feed in feeds_list


@responses.activate
def test_generate_feeds_max_time():
    max_time = 0.5
    num_feeds = 10

    url = 'http://nopenopenope.nope'

    rss_feed_template = '<link type="application/rss+xml" href="{}" />'
    rss_text, rss_links = [], []

    def request_callback(request):
        time.sleep(2 * max_time / num_feeds)
        return (200, {}, '<?xml version="1.0"?> <rss version="2.0"></rss>')

    for idx in range(num_feeds):
        rss_links.append(url + '/{}.rss'.format(idx))
        rss_text.append(rss_feed_template.format(rss_links[-1]))
        responses.add_callback(responses.GET, rss_links[-1], callback=request_callback)
    html = "<html><head>{}</head><body></body></html>".format('\n'.join(rss_text))
    responses.add(responses.GET, url, body=html, status=200)

    discovered = []
    # Make sure it can raise, but get partial results
    with pytest.raises(TimeoutError):
        for feed in feed_seeker.generate_feed_urls(url, max_time=max_time):
            discovered.append(feed)
    assert len(discovered) > 2  # will probably get 4, but this is fine

    def request_callback(request):
        return (200, {}, '')

    # make sure it doesn't always raise
    url = 'http://yupyupyup.yup'
    responses.add(responses.GET, url, body='', status=200)
    list(feed_seeker.generate_feed_urls(url, max_time=max_time))


class TestFeedSeeker(object):
    def setup_method(self):
        responses.start()

        self.base_url = 'http://nopenopenope.nope'
        self.regular_html_template = "<html><head>{head}</head><body>{body}</body></html>"
        self.rss_feed_template = '<link type="application/rss+xml" href="{}" />'
        self.regular_feed_page = '<?xml version="1.0"?> <rss version="2.0"></rss>'

    def teardown_method(self):
        responses.stop()
        responses.reset()

    def test_is_feed(self):
        finder = feed_seeker.FeedSeeker(self.base_url, html=self.regular_feed_page)
        assert finder.is_feed()
        finder = feed_seeker.FeedSeeker(self.base_url, html=self.regular_html_template)
        assert not finder.is_feed()

    def test_html_property(self):
        responses.add(responses.GET, self.base_url, body=self.regular_html_template, status=200)
        finder = feed_seeker.FeedSeeker(self.base_url)
        found_html = finder.html
        assert found_html == self.regular_html_template

    def generate_responses(self):
        feeds = (
            '/get_your_news_here.html',  # will be found in <head>
            '{}/atom.rss'.format(self.base_url),  # will be found in <body>
            '/index.xml',  # hidden!  will still get spotted
        )

        non_feeds = (
            '/not_a_feed.rss',  # will be in <head>
            '/rss.atom',  # will be in <body>
            '/atom.xml',  # hidden, but not 404
        )

        html = self.regular_html_template.format(
            head=self.rss_feed_template.format(feeds[0]),
            body='<a href="{}"></a>'.format(feeds[1])
        )

        assert feeds[0] in html
        assert feeds[1] in html
        assert feeds[2] not in html

        responses.add(responses.GET, self.base_url, body=html, status=200)

        for feed in feeds:
            if not feed.startswith(self.base_url):
                feed = self.base_url + feed
            responses.add(responses.GET, feed, body=self.regular_feed_page, status=200)

        for feed in non_feeds[:-1]:
            responses.add(responses.GET, self.base_url + feed,
                          body=self.regular_html_template, status=200)

        # handle bad statuses
        responses.add(responses.GET, self.base_url + non_feeds[-1],
                      body=self.regular_html_template, status=500)

        return feeds, non_feeds

    def test_spider(self):
        steps = 5
        urls, feeds = [], []
        for step in range(steps):
            html = self.regular_html_template.format(
                head=self.rss_feed_template.format('/{}.rss'.format(step)),
                body='<a href="/{}.html"'.format(step + 1))
            urls.append(self.base_url + '/{}.html'.format(step))
            feeds.append(self.base_url + '/{}.rss'.format(step))
            responses.add(responses.GET, urls[-1], body=html, status=200)
            responses.add(responses.GET, feeds[-1], body=self.regular_feed_page, status=200)

        for j in range(steps - 1):
            found_feeds = list(feed_seeker.generate_feed_urls(urls[0], spider=j))
            assert feeds[:j + 1] == found_feeds

    def test_generate_feed_urls(self):
        feeds, _ = self.generate_responses()

        finder = feed_seeker.FeedSeeker(self.base_url)
        found_feeds = list(finder.generate_feed_urls())

        assert len(found_feeds) == len(feeds)

    def test_generate_feed_urls_max_links(self):
        feeds, _ = self.generate_responses()

        finder = feed_seeker.FeedSeeker(self.base_url)
        max_links = 2
        found_feeds = list(finder.generate_feed_urls(max_links=max_links))

        assert len(found_feeds) > 0
        assert len(found_feeds) <= max_links < len(feeds)

    def test_generate_feed_urls_function(self):
        feeds, _ = self.generate_responses()

        found_feeds = list(feed_seeker.generate_feed_urls(self.base_url))

        assert len(found_feeds) == len(feeds)

    def test_generate_feed_urls_not_a_page(self):
        feeds, _ = self.generate_responses()

        finder = feed_seeker.FeedSeeker(self.base_url + '/what_is_this_even')
        found_feeds = list(finder.generate_feed_urls())

        assert len(found_feeds) == 0

    def test_generate_feed_urls_on_feed(self):
        feeds, _ = self.generate_responses()

        finder = feed_seeker.FeedSeeker(self.base_url + feeds[0])
        found_feeds = list(finder.generate_feed_urls())

        assert len(found_feeds) == 1

    def test_find_feed_url(self):
        feeds, _ = self.generate_responses()

        url = feed_seeker.find_feed_url(self.base_url)
        assert url == self.base_url + feeds[0]

    def test_find_link_feeds(self):
        num_feeds = 4
        feed_urls = []
        # note that we do NOT eliminate duplicates at this level
        for _ in range(num_feeds):
            feed_urls.append(self.rss_feed_template.format('http://whatever.com'))

        html = self.regular_html_template.format(head='\n'.join(feed_urls), body='')
        finder = feed_seeker.FeedSeeker(self.base_url, html=html)
        assert len(list(finder.find_link_feeds())) == num_feeds
        assert len(list(finder.find_anchor_feeds())) == 0

    def test_find_anchor_feeds(self):
        num_feeds = 4
        feed_urls = []
        # we should find these four links
        for feed in range(num_feeds):
            feed_urls.append('<a href="http://{}.rss"></a>'.format(feed))

        # but will not flag this one, since it does not look like a feed
        feed_urls.append('<a href="https://not_an_example.com"></a>')

        html = self.regular_html_template.format(head='', body='\n'.join(feed_urls))
        finder = feed_seeker.FeedSeeker(self.base_url, html=html)
        assert len(list(finder.find_link_feeds())) == 0
        assert len(set(finder.find_anchor_feeds())) == num_feeds

    def test_find_internal_links(self):
        self.generate_responses()
        finder = feed_seeker.FeedSeeker(self.base_url, html=None)
        internal_links = finder.find_internal_links()
        assert len(internal_links) == 1  # from `self.generate_responses`

    def test_guess_feed_links(self):
        # even empty page has some guesses
        finder = feed_seeker.FeedSeeker(self.base_url, html=self.regular_html_template)
        guessed_links = list(finder.guess_feed_links())
        assert len(guessed_links) > 0
        for feed_link in guessed_links:
            assert self.base_url in feed_link

    def test_empty_page(self):
        finder = feed_seeker.FeedSeeker(self.base_url, html=self.regular_html_template)
        # Page has no links, so should fail
        assert finder.find_feed_url() is None

class TestFetcherFunction(object):
    """
    tests for user supplied fetcher function
    """

    def setup_method(self):
        self.base_url = 'http://nopenopenope.nope'
        self.regular_feed_page = '<?xml version="1.0"?> <rss version="2.0"></rss>'
        self.html_page = "<html><head>foo</head><body></body></html>"

    def test_feedseeker_fetcher_homepage(self):
        # if homepage is RSS, nothing else will be fetched
        def fetcher(url):
            return self.regular_feed_page
        finder = feed_seeker.FeedSeeker(self.base_url, fetcher=fetcher)
        feed_urls = list(finder.generate_feed_urls(spider=0, max_links=None))
        assert len(feed_urls) == 1

    def test_feedseeker_fetcher(self):
        # HTML home page
        self.feeds_fetched = 0
        def fetcher(url):
            if url == self.base_url:
                return self.html_page
            self.feeds_fetched += 1
            return self.regular_feed_page
        finder = feed_seeker.FeedSeeker(self.base_url, fetcher=fetcher)
        feed_urls = list(finder.generate_feed_urls(spider=0, max_links=None))
        assert self.feeds_fetched > 1 and len(feed_urls) == self.feeds_fetched

    def test_feedseeker_fetcher_limit(self):
        # HTML home page, test fetcher "error" response
        self.feeds_fetched = 0
        limit = 10
        def fetcher(url):
            if url == self.base_url:
                return self.html_page
            if self.feeds_fetched == limit:
                return ''       # error response?!
            self.feeds_fetched += 1
            return self.regular_feed_page
        finder = feed_seeker.FeedSeeker(self.base_url, fetcher=fetcher)
        feed_urls = list(finder.generate_feed_urls(spider=0, max_links=None))
        assert self.feeds_fetched == limit and len(feed_urls) == self.feeds_fetched

    def test_generate_fetcher(self):
        self.feeds_fetched = 0
        def fetcher(url):
            if url == self.base_url:
                return self.html_page
            self.feeds_fetched += 1
            return self.regular_feed_page
        feed_urls = list(feed_seeker.generate_feed_urls(self.base_url, fetcher=fetcher))
        assert self.feeds_fetched > 1 and len(feed_urls) == self.feeds_fetched
