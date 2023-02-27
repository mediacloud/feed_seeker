import os
import sys
import os.path
import time
import pandas as pd
import config as cfg
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
from feed_seeker import find_feedly_feeds

# script to find feeds for websites listed in file sources.csv using feedly.
# use a proxy service to access feedly since running multiple threads will cause an ip to get banned

# run feedly for a data source to find the feeds
def getFeed(source, output_dir, proxy):
    retry_flag = True
    retry_count = 0
    retry_second = 3
    retry_num = 8
    while retry_flag and retry_count < retry_num:
        try:
            resp = find_feedly_feeds('https://' + source, proxy=proxy)
            result = []
            for feed in resp:
                print(feed)
                result.append(feed) 
            retry_flag = False
        except Exception as e:
            print(f"Retry after {retry_second*retry_count**2} seconds for {source} due to: {e}")
            retry_count = retry_count + 1
            time.sleep(retry_second * retry_count**2)
    print(result)
    df = pd.DataFrame(result)
    df['source'] = source
    df.to_csv(output_dir + '/' + source + '.csv')
    return source

def get_feeds_for_sources(sources, output_dir, proxy):
    threads= []
    respl = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for source in sources:
            if os.path.exists(output_dir + '/' + source + '.csv'):
                print(f"skipping {source}")
                continue
            sys.stdout.flush()
            file_name = uuid.uuid1()
            threads.append(executor.submit(getFeed, source, output_dir, proxy))
        for task in as_completed(threads):
            symbol = task.result()


proxy = {}
# if using a proxy with feedly you should set https
#proxy = {
#    'http': '',
#    'https': '',
#}
output_dir="feeds"
if not os.path.exists(output_dir):
    os.mkdir(output_dir)

# open the hostnames to get feeds for
df = pd.read_csv("source.csv")
sources = df.domain.values.tolist()
get_feeds_for_sources(sources, output_dir, proxy)
