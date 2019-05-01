"""Class for finding the most likely url for an RSS/atom/other feed on a web page.

See https://github.com/dfm/feedfinder2 for other approaches to the same task.
"""
from contextlib import contextmanager
import signal
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import InvalidSchema, RetryError
from urllib3.util.retry import Retry


@contextmanager
def timeout(seconds=None):
    """Context manager for handling timeouts"""
    if seconds:
        def handler(signum, frame):
            """Handle signal timer"""
            raise TimeoutError('Timeout reached ({}s)'.format(seconds))
        old = signal.signal(signal.SIGALRM, handler)
        signal.setitimer(signal.ITIMER_REAL, seconds)
    yield
    if seconds:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def _is_feed_url(url):
    """Check if a url is a feed url with high confidence

    Wraps custom logic for high probability checks.

    Parameters
    ----------
    url : str
          Url that may or may not be a feed

    Returns
    -------
    boolean
        True if the string is a feed with high probability, or else False
    """
    endings = (
        '.rss',
        '.rdf',
        '.atom',
        '.xml',
    )
    url_lower = url.lower()
    return any(url_lower.endswith(ending) for ending in endings)


def _might_be_feed_url(url):
    """Check if a url might be a feed with moderate confidence

    A lower trust version of `_is_feed_url`
    Parameters
    ----------
    url : str
          Url that may or may not be a feed

    Returns
    -------
    boolean
        True if the string is a feed with reasonable probability, or else False
    """
    substrings = (
        'rss',
        'rdf',
        'atom',
        'xml',
        'feed'
    )
    url_lower = url.lower()
    return any(substring in url_lower for substring in substrings)


def default_fetch_function(url):
    """Default function to fetch text from url

    There are some strong choices on how to handle errors in `FeedSeeker`. Use this function
    as an example of how to make a new fetch function. Note that the function may be used
    to attempt to fetch urls that do not exist, so be thoughtful about what exceptions to throw!

    Parameters
    ----------
    url : string
        A url for a webpage

    Returns
    ------
    str
        Text of the html from the url
    """

    session = requests.Session()

    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session.mount(url, HTTPAdapter(max_retries=retries))
    try:
        response = session.get(url)
        if response.ok:
            return response.text
        else:
            return ''

    # ConnectionError for 404s, InvalidSchema for email addresses
    except (requests.ConnectionError, InvalidSchema, RetryError, requests.TooManyRedirects):
        return ''


class FeedSeeker(object):
    """A class to find possible RSS/Atom feeds on a web page.

    Usually easier to use `find_feed_url` or `generate_feed_urls`.
    The class defines a few methods for discovering links on a page, from
    first looking for standard feed links, then looking for *any* link, and then
    guessing at a few urls that are commonly used for feeds.  See
    `find_link_feeds`, `find_anchor_feeds`, and `guess_feed_links`, respectively.

    The class is used by either asking for a single feed, or all feeds.  All web
    fetching is deferred until needed, so it is typically much faster to only
    get a single feed, or to stop iterating over all feeds once a condition is
    satisfied.
    """
    def __init__(self, url, html=None, fetcher=None):
        """Initialization

        Parameters
        ----------
        url : str
              A url that resolves to the webpage in question

        html : str (optional)
              To save a second web fetch, the raw html can be supplied
        fetcher : function (optional)
              A function that accepts a url and returns text. See `default_fetch_function`
              for how to write a custom fetcher.
        """
        self.url = url
        self._html = html
        self._soup = None
        self.fetcher = fetcher or default_fetch_function

    @property
    def html(self):
        """String of the html of the underlying site."""
        if self._html is None:
            self._html = self.fetcher(self.url)
        return self._html

    @property
    def soup(self):
        """BeautifulSoup representation of the data."""
        if self._soup is None:
            self._soup = BeautifulSoup(self.html, 'lxml')
        return self._soup

    def clean_url(self):
        """Remove query arguments from a url."""
        parsed = urlparse(self.url)
        return urlunparse(parsed._replace(query=''))

    def _should_continue(self, seen, max_links):
        """Helper to short-circuit spidering
        Parameters
        ----------
        seen : set
            List of urls that have already been checked
        max_links : int or None
            Maximum number of links to check

        Returns
        ------
        boolean
            True if no stop condition has been met, False otherwise
        """
        if max_links is not None and len(seen) >= max_links:
            return False
        return True

    def generate_feed_urls(self, spider=0, max_links=None):
        """Generates an iterator of possible feeds, in rough order of likelihood.

        Parameters
        ----------
        spider : int (optional)
              How many times to restart the seeker on links with the same hostname on this page
        max_links : int (optional)
              Maximum links to check as feeds, to limit spidering complexity. Defaults to `None`,
              for unlimited.

        Yields
        ------
            urls of possible feeds
        """
        for url, _ in self._generate_feed_urls(spider=spider, max_links=max_links):
            yield url

    def _generate_feed_urls(self, spider=0, seen=None, max_links=None):
        """Internal function that actually does the work for `generate_feed_urls`

        There are some recursive calls keeping track of already seen urls, and it was easier
        to do it this way.

        Parameters
        ----------
        spider : int (optional)
              How many times to restart the seeker on links with the same hostname on this page
        seen : set
            (Optional) list of urls to not produce. May be used as a blacklist.
        max_links : int (optional)
              Maximum links to check as feeds, to limit spidering complexity. Defaults to `None`,
              for unlimited.

        Yields
        ------
            (string, set)
            urls of possible feeds, and all the urls already seen
        """
        if seen is None:
            seen = set()

        if not self.html:
            return

        if self.is_feed() and self.url not in seen:
            seen.add(self.url)
            yield self.url, seen
            return

        for url_fn in (self.find_link_feeds, self.find_anchor_feeds, self.guess_feed_links):
            for url in url_fn():
                if url not in seen:
                    seen.add(url)
                    if not self._should_continue(seen, max_links):
                        return
                    if FeedSeeker(url).is_feed():
                        yield url, seen

        if spider > 0:
            for internal_link in self.find_internal_links():
                spider_seeker = FeedSeeker(internal_link, html=None, fetcher=self.fetcher)
                kwargs = {
                    'spider': spider - 1,
                    'seen': seen,
                    'max_links': max_links,
                }
                for url, seen in spider_seeker._generate_feed_urls(**kwargs):
                    yield url, seen

    def find_feed_url(self, spider=0, max_links=None):
        """Fine the single most likely url as a feed for the page, or None.

        Parameters
        ----------
        spider : int (optional)
              How many times to restart the seeker on links with the same hostname on this page
        max_links : int (optional)
              Maximum links to check as feeds, to limit spidering complexity. Defaults to `None`,
              for unlimited.

        Returns
        -------
        str
            The most likely url to have a feed for this page
        """

        try:
            return next(self.generate_feed_urls(spider=spider, max_links=max_links))
        except StopIteration:
            return None

    def is_feed(self):
        """Check if the site is a feed.

        Logic is to make sure there is no <html> tag, and there is some <rss> tag or similar.
        """
        invalid_tags = ('head',)
        if any(self.soup.find(tag) for tag in invalid_tags):
            return False

        valid_tags = ('rss', 'rdf', 'feed',)
        return any(self.soup.find(tag) for tag in valid_tags)

    def find_link_feeds(self):
        """Uses <link> tags to extract feeds

        for example:
            <link type="application/rss+xml" href="/might/be/relative.rss"></link>
        """
        valid_types = [
            "application/rss+xml",
            "text/xml",
            "application/atom+xml",
            "application/x.atom+xml",
            "application/x-atom+xml"
        ]

        for link in self.soup.find_all('link', type=valid_types):
            url = link.get('href')
            if url:
                yield urljoin(base=self.clean_url(), url=url)

    def find_internal_links(self):
        """Finds <a></a> tags to internal pages on the same domain that may have a feed.

        For example, this may find the homepage, or an index page.
        """
        parsed_url = urlparse(self.clean_url())
        parts = set(filter(None, parsed_url.path.split('/')))
        possible_links = []
        for link_node in self.soup.find_all('a', href=True):
            link = link_node.get('href')
            parsed_link = urlparse(link)
            if not parsed_link.hostname:
                parsed_link = parsed_link._replace(netloc=parsed_url.hostname,
                                                   scheme=parsed_url.scheme)
                link = urlunparse(parsed_link)
            if parsed_link.hostname == parsed_url.hostname:
                might_be_feed = any(check(link) for check in (_is_feed_url, _might_be_feed_url))
                link_parts = set(filter(None, parsed_link.path.split('/')))
                similarity = len(parts.intersection(link_parts)) + might_be_feed * len(parts)
                possible_links.append((link, similarity))
        return [link for link, _ in sorted(set(possible_links), key=lambda j: (-j[1], len(j[0])))]

    def find_anchor_feeds(self):
        """Uses <a></a> tags to extract feeds

        for example
            <a href="https://www.whatever.com/rss"></a>
        """
        # This is outer loop so that most likely links
        # are produced first
        for url_filter in (_is_feed_url, _might_be_feed_url):
            for link in self.soup.find_all('a', href=True):
                url = link.get('href')
                if url_filter(url):
                    yield urljoin(base=self.clean_url(), url=url)

    def guess_feed_links(self):
        """Iterates common locations to find feeds.  These urls probably do not exist, but might

        Manual overrides should be added here.  For example, if foo.com has their rss feed at
        foo.com/here/for/reasons.rss, add 'here/for/reasons.rss' to the suffixes.
        """
        suffixes = (
            # Generic suffixes
            'index.xml', 'atom.xml', 'feeds', 'feeds/default', 'feed', 'feed/default',
            'feeds/posts/default/', '?feed=rss', '?feed=atom', '?feed=rss2', '?feed=rdf', 'rss',
            'atom', 'rdf', 'index.rss', 'index.rdf', 'index.atom',
            '?type=100',  # Typo3 RSS URL
            '?format=feed&type=rss',  # Joomla RSS URL
            'feeds/posts/default',  # Blogger.com RSS URL
            'data/rss',  # LiveJournal RSS URL
            'rss.xml',  # Posterous.com RSS feed
            'articles.rss', 'articles.atom',  # Patch.com RSS feeds
        )
        for suffix in suffixes:
            yield urljoin(base=self.clean_url(), url=suffix)


def find_feed_url(url, html=None, spider=0, max_time=None, max_links=None):
    """Find the single most likely feed url for a page.

    Parameters
    ----------
    url : str
          A url that resolves to the webpage in question
    html : str (optional)
          To save a second web fetch, the raw html can be supplied
    spider : int (optional)
          How many times to restart the seeker on links with the same hostname on this page
    max_time : float (optional)
          Give up after a certain amount of time. This is a lower limit, in that time
          is checked *after* each request returns. Defaults to `None` for unlimited. Will
          throw a TimeoutError if reached
    max_links : int (optional)
          Maximum links to check as feeds, to limit spidering complexity. Defaults to `None`,
          for unlimited.


    Returns
    -------
    str or None
       A url pointing to the most likely feed, if it exists.
    """
    with timeout(max_time):
        return FeedSeeker(url, html).find_feed_url(spider=spider, max_links=max_links)


def generate_feed_urls(url, html=None, spider=0, max_time=None, max_links=None):
    """Find all feed urls for a page.

    Parameters
    ----------
    url : str
          A url that resolves to the webpage in question
    html : str (optional)
          To save a second web fetch, the raw html can be supplied
    spider : int (optional)
          How many times to restart the seeker on links with the same hostname on this page
    max_time : float (optional)
          Give up after a certain amount of time. This is a lower limit, in that time
          is checked *after* each request returns. Defaults to `None` for unlimited. Throws
          a TimeoutError when the time is reached
    max_links : int (optional)
          Maximum links to check as feeds, to limit spidering complexity. Defaults to `None`,
          for unlimited.

    Yields
    ------
    str or None
       A url pointing to a feed associated with the page
    """
    with timeout(max_time):
        for feed in FeedSeeker(url, html).generate_feed_urls(spider=spider, max_links=max_links):
            yield feed
