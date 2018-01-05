===========
Feed Seeker
===========
*It slant rhymes with "heat seeker"*

A library for finding atom, rss, rdf, and xml feeds from web pages. Produced at the `mediacloud <https://mediacloud.org>`_ project. An incremental improvement over `feedfinder2 <https://github.com/dfm/feedfinder2>`_, which was itself based on `feedfinder <http://www.aaronsw.com/2002/feedfinder/>`_, written by Mark Pilgrim, and maintained by Aaron Swartz until his untimely death. 

Quickstart
==========
The library uses :code:`requests` to grab html and inspect it:

.. code-block:: python
   
   from feed_seeker import find_feed_url, generate_feed_urls

   find_feed_url('http://xkcd.com')             # 'http://xkcd.com/atom.xml'
   list(generate_feed_urls('http://xkcd.com'))  # ['http://xkcd.com/atom.xml', 
                                                #  'http://xkcd.com/rss.xml']



Differences with :code:`feedfinder2`
====================================
The biggest difference is that all functions are implemented as generators, and are evaluated lazily. Candidate feed links are actually accessed and inspected to determine whether or not they are a feed, which can be quite time consuming. We expose a function to find the most likely feed link, and another to lazily generate links in rough order from most prominent to least.

There are also a few more heuristics based on our experience at `mediacloud <https://mediacloud.org>`_.
