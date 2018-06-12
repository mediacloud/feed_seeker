import csv
from feed_seeker import *

feed_list = set()

with open("feed_seeker/answers.csv") as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='|')
    for row in reader:
        feed_list.add((row[0],row[1]))

print(feed_list)

with open("feed_seeker/predictions_baseline.csv", "w") as csvfile:
    writer = csv.writer(csvfile, delimiter=',')
    for url in feed_list:
        for feed in generate_feed_urls(url[1]):
            writer.writerow([url[0], url[1], feed])