import sys
from argparse import ArgumentParser

from feed_seeker import find_feed_url, find_feedly_feeds, generate_feed_urls

# TODO: Used for tests, remove
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
    psr.add_argument(
        "--all", help="Find all feeds under the provided URL", action="store_true"
    )
    psr.add_argument(
        "--feedly",
        help="Find all feeds under the provided URL using Feedly, takes precedence over '--all'",
        action="store_true",
    )
    args = psr.parse_args()

    defaults = {action.dest: action.default for action in psr._actions}

    feed_urls = []
    if args.feedly:
        feedly_ignored_args = ["html", "spider", "max-time", "all"]
        for arg_name in feedly_ignored_args:
            py_arg_name = arg_name.replace("-", "_")
            default_val = defaults[py_arg_name]
            current_val = getattr(args, py_arg_name)
            if default_val != current_val:
                print(f"--{arg_name} is ignored when --feedly is used", file=sys.stderr)
        feed_urls += list(find_feedly_feeds(args.url, max_links=args.max_links))
    elif args.all:
        feed_urls += list(
            generate_feed_urls(
                args.url,
                html=args.html,
                spider=args.spider,
                max_time=args.max_time,
                max_links=args.max_links,
            )
        )
    else:
        feed_url = find_feed_url(
            args.url,
            html=args.html,
            spider=args.spider,
            max_time=args.max_time,
            max_links=args.max_links,
        )
        if feed_url is not None:
            feed_urls.append(feed_url)

    if len(feed_urls) == 0:
        print("No feed found", file=sys.stderr)
        sys.exit(1)

    for feed_url in feed_urls:
        print(feed_url)


if __name__ == "__main__":
    main()
