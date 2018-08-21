import argparse
import sys
import time
from queue import Empty
from urllib.parse import urlparse

import requests
import bs4
from multiprocessing import Queue, Pool, Manager, cpu_count
from urllib.parse import urljoin

# Seed data
WIKI_BASE = 'https://en.wikipedia.org/'
KEVIN_BACON = 'https://en.wikipedia.org/wiki/Kevin_Bacon'
FOOTLOOSE = 'https://en.wikipedia.org/wiki/Footloose_(1984_film)'
GOOD_MEN = 'https://en.wikipedia.org/wiki/A_Few_Good_Men'
TOM_CRUISE = 'https://en.wikipedia.org/wiki/Tom_Cruise'
SORKIN = 'https://en.wikipedia.org/wiki/Aaron_Sorkin'


class BaconDegrees:
    # Degrees of separation
    deg = Queue()
    # Primary queue where the workers select the next uri from.
    # 0-20000 elements are for active usage.
    # 20000-32000 are for holding URLS while waiting for space in the buffer of first 20000 to free up
    q = Queue(32000)
    # Size of self.q : This is needed since multiprocessing.Queue.qsize() is not implemented for macs
    qsize = Queue()
    # Set of explored URIs
    explored = set()
    # Timeout (in seconds) for getting elements from a queue.
    TIMEOUT = 5

    # Get links
    def get_links(self, init_uri=FOOTLOOSE):
        if not isinstance(init_uri, str):
            return []
        if not init_uri.startswith('http'):
            return []

        response = requests.get(init_uri)
        soup = bs4.BeautifulSoup(response.content, 'html.parser')

        wiki_set = set()
        images = set(['.png', '.svg', '.jpg'])

        for link in soup.find_all('a'):
            href = link.get('href')
            if href and href.startswith('/wiki'):
                extension = href[len(href)-4:len(href)]
                if extension not in images:
                    href = urljoin(WIKI_BASE, href)
                    wiki_set.add(href)

        return sorted(list(wiki_set))

    # Checks all the links on the current page first, before enqueing them.
    def pre_enque_check(self, target_uri, wiki_links):
        for link in wiki_links:
            if link == target_uri:
                return link
        return False

    # Explore the graph
    def explore(self, target_uri, event=None):
        while not event.is_set():
            try:
                path = self.q.get(timeout=self.TIMEOUT)
            except Empty:
                self.deg.put([])
                event.set()
                return

            node = path[-1]

            if node == target_uri:
                self.deg.put(path)
                if event:
                    event.set()
                return

            self.explored.add(node)
            wiki_links = self.get_links(node)

            # Checks all the links on the current page first, before enqueing them.
            check_link = self.pre_enque_check(target_uri, wiki_links)
            if check_link:
                path.append(check_link)
                self.deg.put(path)
                if event:
                    event.set()
                return

            qs = self.qsize.get()
            new_size = qs + len(wiki_links)

            # If there is not enough size in self.q[0:20000], then URL is put back in self.q[20000:32000]
            # to be explored later again. It's child nodes are not put on the queue since there is no space in
            # the buffer space of the first 20000 elements of self.q
            if new_size >= 20000:
                self.qsize.put(qs)
                self.q.put(path)
                continue

            # There was enough space on self.q. Let's insert the new links in self.q.
            self.qsize.put(new_size-1)
            for link in wiki_links:
                if link not in self.explored:
                    new_path = path[:]
                    new_path.append(link)
                    self.q.put(new_path)

    # Driver function which spins up a worker_pool and runs the explore() function
    def get_degrees(self, start_uri=GOOD_MEN, target_uri=KEVIN_BACON):
        validation = self.validate_urls([start_uri, target_uri])

        worker_pool = Pool(cpu_count())
        worker_manager = Manager()
        event = worker_manager.Event()

        self.q.put([start_uri])
        self.qsize.put(1)

        # Start up all the workers in the pool
        for i in range(cpu_count()):
            worker_pool.apply_async(self.explore, (target_uri, event))

        event.wait()
        worker_pool.terminate()

        try:
            path = self.deg.get(timeout=self.TIMEOUT)
        except Empty:
            return [], -1
        degrees = len(path) - 1
        return path, degrees

    # Parse command line arguments
    def get_parser(self):
        parser = argparse.ArgumentParser(description='Degrees of separation')
        parser.add_argument('--start', dest='start_uri', default=GOOD_MEN, help='The URI from which to start the search')
        parser.add_argument('--target', dest='target_uri', default=KEVIN_BACON, help='The target URI to arrive at')

        return parser

    # Validate that the URLs are in Wikipedia
    def validate_urls(self, urls):
        if urls == [] or urls == '':
            raise ValueError('Please enter start and target URLs')

        for url in urls:
            parsed_url = urlparse(url)
            if not parsed_url.netloc.endswith('wikipedia.org'):
                message = '{} is not a valid Wikipedia URL'.format(url)
                raise ValueError(message)

            # Validate that the URI actually exists in Wikipedia
            response = requests.get(url)
            if response.status_code != 200:
                message = '{} is a bad URI. Status code:{}'.format(url, response.status_code)
                raise ValueError(message)

        return True


if __name__ == '__main__':
    start_time = time.time()

    kbacon = BaconDegrees()
    parser = kbacon.get_parser()
    args = parser.parse_args()
    print('\nStart URL: {} \nTarget URL: {}'.format(args.start_uri, args.target_uri))

    path, degrees = kbacon.get_degrees(args.start_uri, args.target_uri)
    print('Degrees: ', degrees)
    print('Path:')
    for p in path:
        print('    ', p)

    print('\nRun time: %s seconds' % (time.time() - start_time))
