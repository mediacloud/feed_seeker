import sys
from argparse import ArgumentParser
from feed_seeker import find_feed_url, generate_feed_urls, find_feedly_feeds
# https://ici.radio-canada.ca/rss


def main():
    # TODO: Write tests for the CLI
    psr = ArgumentParser(
        prog="feed_seeker", description="Find the most likely feed URL for a webpage"
    )
    psr.add_argument("url", help="URL of the webpage to search from")
    psr.add_argument("--html", help="Optional raw HTML t save a second web fetch")
    psr.add_argument(
        "--spider",
        help="How many times to restart the seeker on links with the same hostname on this page",
        type=int,
        default=0,
    )
    psr.add_argument(
        "--max-time",
        help="Max time allowed for a request to return something",
        default=None,
        type=float,
    )
    psr.add_argument(
        "--max-links", help="Maximum links to check as feeds.", type=int, default=None
    )
    psr.add_argument("--all", help="Find all feeds under the provided URL", action="store_true")
    psr.add_argument("--feedly", help="Find all feeds under the provided URL using Feedly, takes precedence over '--all'", action="store_true")
    args = psr.parse_args()


    feed_urls = []
    # TODO: Handle args that are not used by feedly
    if args.feedly:
        feed_urls += list(find_feedly_feeds(args.url, max_links=args.max_links))
    elif args.all:
        feed_urls += list(generate_feed_urls(args.url, htø=args.html, spider=args.spider, max_time=args.max_time, max_links=args.max_links))
    else:
        feed_url = find_feed_url(args.url, html=args.html, spider=args.spider, max_time=args.max_time, max_links=args.max_links)
        if feed_url is not None:
            feed_urls.append(feed_url)

    if len(feed_urls) == 0:
        print("No feed found", file=sys.stderr)
        sys.exit(1)

    for feed_url in feed_urls:
        print(feed_url)


if __name__ == "__main__":
    main()
