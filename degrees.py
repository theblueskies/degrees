import sys
import time

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
    # Primary queue where the workers select the next uri from
    q = Queue(32000)
    # Overflow queue
    overflow_q = Queue(32000)
    # Size of Q. This is needed since multiprocessing.Queue.qsize() is not implemented for macs
    qsize = Queue()
    # Set of explored URIs
    explored = set()

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

    # Explore the graph
    def explore(self, event, target_uri):
        while not self.q.empty() or not self.overflow_q.empty():
            if not self.q.empty():
                path = self.q.get()
            else:
                print ('QEMPTY')
                path = self.overflow_q.get()
            node = path[-1]
            print(path)

            if node == target_uri:
                calc_degree = len(path) - 1
                self.deg.put(calc_degree)
                event.set()
                return

            self.explored.add(node)
            wiki_links = self.get_links(node)

            qs = self.qsize.get()
            new_size = qs + len(wiki_links)
            print('QSIZE: {} ... NEW SIZE: {}'.format(qs, new_size))

            # If there is not enough size in Q, then it is stored in self.overflow_q and cycled back
            # in once Q has space available on it again.
            if new_size >= 32000:
                self.qsize.put(qs-1)
                self.overflow_q.put(path)
                continue

            self.qsize.put(new_size-1)
            for link in wiki_links:
                if link not in self.explored:
                    new_path = path[:]
                    new_path.append(link)

                    self.q.put(new_path)

        print('Q is empty')
        event.set()

    # Driver function which spins up a worker_pool and runs the explore() function
    def get_degrees(self, start_uri=TOM_CRUISE, target_uri=KEVIN_BACON):
        worker_pool = Pool(cpu_count())
        worker_manager = Manager()
        event = worker_manager.Event()

        self.q.put([start_uri])
        self.qsize.put(1)

        worker_pool.apply_async(self.explore, (event, target_uri))
        event.wait()
        worker_pool.terminate()

        d = self.deg.get()
        return d


if __name__ == '__main__':
    start_time = time.time()
    kbacon = BaconDegrees()

    print(kbacon.get_degrees(TOM_CRUISE, KEVIN_BACON))
    print("--- %s seconds ---" % (time.time() - start_time))
