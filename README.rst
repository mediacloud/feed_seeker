===========
Feed Seeker
===========

*It slant rhymes with "heat seeker"*

|Build Status| |Coverage|

A library for finding atom, rss, rdf, and xml feeds from web pages. Produced at the `mediacloud <https://mediacloud.org>`_ project. An incremental improvement over `feedfinder2 <https://github.com/dfm/feedfinder2>`_, which was itself based on `feedfinder <http://www.aaronsw.com/2002/feedfinder/>`_, written by Mark Pilgrim, and maintained by Aaron Swartz until his untimely death. 


Installation
------------

The library is available on `PyPI <https://pypi.org/project/feed_seeker/>`_:

.. code-block:: bash

    pip install feed_seeker

The library requires Python 3.5+.


Quickstart
----------
By default, the library uses :code:`requests` to grab html and inspect it and find the most
likely feed url:

.. code-block:: python

    from feed_seeker import find_feed_url

    >>> find_feed_url('https://github.com/mitmedialab/feed_seeker') 
    'https://github.com/mitmedialab/feed_seeker/commits/master.atom'

To do a more thorough search, use :code:`generate_feed_urls`, which returns more likely candidates first.

.. code-block:: python

    from feed_seeker import generate_feed_urls
    
    >>> for url in generate_feed_urls('https://xkcd.com'):
    ...     print(url)
    ... 
    https://xkcd.com/atom.xml
    https://xkcd.com/rss.xml

For the most thorough search, add a :code:`spider` argument to do depth-first spidering of urls on the same hostname. Note the below call takes nearly four minutes, compared to 0.5 seconds for :code:`find_feed_url`.

.. code-block:: python

    >>> for url in generate_feed_urls('https://github.com/mitmedialab/feed_seeker', spider=1):
    ...     print(url)
    ... 
    https://github.com/mitmedialab/feed_seeker/commits/master.atom,
    https://github.com/mitmedialab/feed_seeker/commits/95cf320796c487df8b70f9c42281d8f26452cc31.atom,
    https://github.com/mitmedialab/feed_seeker/commits/3e93490cb91f7652325c2fe41ef29a5be4558d6a.atom,
    https://github.com/mitmedialab/feed_seeker/commits/659311b8853c4c4a67e3b4bc67a78461d825a064.atom,
    https://github.com/mitmedialab/feed_seeker/commits/a8f7b86eac2cedd9209ac5d2ddcceb293d2404c9.atom,
    https://github.com/index.atom,
    https://github.com/articles.atom,
    https://github.com/dfm/feedfinder2/commits/master.atom,
    https://github.com/blog.atom,
    https://github.com/blog/all.atom,
    https://github.com/blog/broadcasts.atom,
    https://github.com/ColCarroll.atom


In a hurry?
-----------

If you have a long list of urls, you might want to set a timeout with :code:`max_time`:

.. code-block:: python

    >>> for url in ('https://httpstat.us/200?sleep=5000', 'https://github.com/mitmedialab/feed_seeker'):
       ...     try:
       ...         print('found feed:\t{}'.format(find_feed_url(url, max_time=3)))
       ...     except TimeoutError:
       ...         print('skipping {}'.format(url))
       skipping https://httpstat.us/200?sleep=5000
       found feed:  https://github.com/mitmedialab/feed_seeker/commits/master.atom


Differences with :code:`feedfinder2`
====================================
The biggest difference is that all functions are implemented as generators, and are evaluated lazily. Candidate feed links are actually accessed and inspected to determine whether or not they are a feed, which can be quite time consuming. We expose a function to find the most likely feed link, and another to lazily generate links in rough order from most prominent to least.

There are also a few more heuristics based on our experience at `mediacloud <https://mediacloud.org>`_.

.. |Build Status| image:: https://travis-ci.org/mitmedialab/feed_seeker.png?branch=master
   :target: https://travis-ci.org/mitmedialab/feed_seeker
.. |Coverage| image:: https://coveralls.io/repos/github/mitmedialab/feed_seeker/badge.svg?branch=master
   :target: https://coveralls.io/github/mitmedialab/feed_seeker?branch=master
