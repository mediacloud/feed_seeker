===========
Feed Seeker
===========
*It slant rhymes with "heat seeker"*

|Build Status| |Coverage|

A library for finding atom, rss, rdf, and xml feeds from web pages. Produced at the `mediacloud <https://mediacloud.org>`_ project. An incremental improvement over `feedfinder2 <https://github.com/dfm/feedfinder2>`_, which was itself based on `feedfinder <http://www.aaronsw.com/2002/feedfinder/>`_, written by Mark Pilgrim, and maintained by Aaron Swartz until his untimely death. 

Quickstart
==========
By default, the library uses :code:`requests` to grab html and inspect it and find the most
likely feed url:

.. code-block:: python
   
   from feed_seeker import find_feed_url

   >>> find_feed_url('https://github.com/ColCarroll/feed_seeker') 
   'https://github.com/ColCarroll/feed_seeker/commits/master.atom'


To do a more thorough search, use :code:`generate_feed_urls`, which returns more likely candidates first.

.. code-block:: python

   from feed_seeker import generate_feed_urls

    >>> for url in generate_feed_urls('https://xkcd.com'):
    ...     print(url)
    ... 
    https://xkcd.com/atom.xml
    https://xkcd.com/rss.xml


 For the most thorough search, add a :code:`spider` argument to do depth-first spidering of urls
 on the same hostname. Note the below call takes nearly four minutes, compared to 0.5 seconds for
 :code:`find_feed_url`.


.. code-block:: python

    >>> for url in generate_feed_urls('https://github.com/ColCarroll/feed_seeker', spider=1):
    ...     print(url)
    ... 
    https://github.com/ColCarroll/feed_seeker/commits/master.atom
    https://github.com/ColCarroll/feed_seeker/commits/a8f7b86eac2cedd9209ac5d2ddcceb293d2404c9.atom
    https://github.com/ColCarroll/feed_seeker/commits/3b5245b46a10fb3647a1f08b8e584b471683fbbd.atom
    https://github.com/ColCarroll/feed_seeker/commits/659311b8853c4c4a67e3b4bc67a78461d825a064.atom
    https://github.com/ColCarroll/feed_seeker/commits/3e93490cb91f7652325c2fe41ef29a5be4558d6a.atom
    https://github.com/index.atom
    https://github.com/articles.atom
    https://github.com/dfm/feedfinder2/commits/master.atom
    https://github.com/ColCarroll.atom
    https://github.com/blog.atom
    https://github.com/blog/all.atom
    https://github.com/blog/broadcasts.atom



Installation
------------

The library is not yet available on PyPI, so installation is via github only for now:

.. code-block:: bash

    pip install git+https://github.com/ColCarroll/feed_seeker
                                                  


Differences with :code:`feedfinder2`
====================================
The biggest difference is that all functions are implemented as generators, and are evaluated lazily. Candidate feed links are actually accessed and inspected to determine whether or not they are a feed, which can be quite time consuming. We expose a function to find the most likely feed link, and another to lazily generate links in rough order from most prominent to least.

There are also a few more heuristics based on our experience at `mediacloud <https://mediacloud.org>`_.

.. |Build Status| image:: https://travis-ci.org/ColCarroll/feed_seeker.png?branch=master
   :target: https://travis-ci.org/ColCarroll/feed_seeker
.. |Coverage| image:: https://coveralls.io/repos/github/ColCarroll/feed_seeker/badge.svg?branch=master
   :target: https://coveralls.io/github/ColCarroll/feed_seeker?branch=master
