def display_startup_graphic():
    print("\033[92m")  # Bright Green color
    print(r"""
   _____ _             _ _   _
  / ____| |           | | | | |
 | (___ | |_ ___  __ _| | |_| |__
  \___ \| __/ _ \/ _` | | __| '_ \
  ____) | ||  __/ (_| | | |_| | | |
 |_____/ \__\___|\__,_|_|\__|_| |_|_
         / ____|                  | |
        | |     _ __ __ ___      _| | ___ _ __
        | |    | '__/ _` \ \ /\ / / |/ _ \ '__|
        | |____| | | (_| |\ V  V /| |  __/ |
         \_____|_|  \__,_| \_/\_/ |_|\___|_|
    """)
    print("\033[0m")  # Reset to default terminal color

    print("\033[93m")  # Bright Yellow color for the description
    print("Stealth Crawler: Advanced web crawler for analyzing and extracting unique query parameters.")
    print("Designed for performance and stealth. Intended for ethical use in security assessments.")
    print("\033[0m")  # Reset to default terminal color again

if __name__ == "__main__":
    display_startup_graphic()
    
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, parse_qs
import argparse
import logging
import sys
from asyncio_throttle import Throttler

logging.basicConfig(filename='crash_log.log', level=logging.ERROR, format='%(asctime)s:%(levelname)s:%(message)s')

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

class StealthCrawler:
    def __init__(self, start_url, max_depth, force_ssl, output_file, threads, rate_limit):
        self.start_url = start_url if start_url.startswith(('http://', 'https://')) else 'http://' + start_url
        self.max_depth = max_depth
        self.force_ssl = force_ssl
        self.output_file = output_file
        self.semaphore = asyncio.Semaphore(threads)
        self.throttler = Throttler(rate_limit=rate_limit)
        self.visited_urls = set()
        self.unique_query_keys = {}  # Back to using a dictionary for simplicity
        self.target_domain = urlparse(self.start_url).netloc

    async def fetch(self, url, session):
        async with self.semaphore, self.throttler:
            try:
                async with session.get(url, headers={'User-Agent': USER_AGENT}, ssl=self.force_ssl) as response:
                    if 'text/html' in response.headers.get('Content-Type', ''):
                        return await response.text()
            except Exception as e:
                logging.error(f"Failed to fetch {url}: {e}")
            return None

    async def parse(self, url, session, depth=1):
        if url in self.visited_urls or depth > self.max_depth:
            return
        self.visited_urls.add(url)
        html = await self.fetch(url, session)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            for link in soup.find_all('a', href=True):
                full_url = urljoin(url, link.get('href'))
                if urlparse(full_url).netloc == self.target_domain:
                    query = urlparse(full_url).query
                    if query:
                        query_keys = tuple(sorted(parse_qs(query).keys()))
                        if query_keys not in self.unique_query_keys:
                            self.unique_query_keys[query_keys] = full_url
                            with open(self.output_file, 'a') as f:
                                f.write(f"{full_url}\n")
                    if full_url not in self.visited_urls:
                        await self.parse(full_url, session, depth + 1)
        print(f"\rVisited URLs: {len(self.visited_urls)}, Unique Parameters: {len(self.unique_query_keys)}", end='', flush=True)

    async def crawl(self):
        async with aiohttp.ClientSession() as session:
            await self.parse(self.start_url, session, 1)

def main():
    parser = argparse.ArgumentParser(description="Stealth URL crawler for analyzing query parameters.")
    parser.add_argument("-u", "--url", required=True, help="The targeted URL to start crawling.")
    parser.add_argument("--depth", type=int, default=2, help="Depth of crawl.")
    parser.add_argument("--ssl", dest="force_ssl", action='store_false', help="Toggle to force SSL as OFF for URLs that require it.")
    parser.add_argument("--output", default="unique_params.txt", help="Output file for unique query parameters.")
    parser.add_argument("--threads", type=int, default=5, help="Number of concurrent requests.")
    parser.add_argument("--rate-limit", type=int, default=1, help="Number of requests per second.")
    
    args = parser.parse_args()
    crawler = StealthCrawler(args.url, args.depth, args.force_ssl, args.output, args.threads, args.rate_limit)

    try:
        asyncio.run(crawler.crawl())
    except KeyboardInterrupt:
        print("\nUser interrupted... Saving found URLs...")
        with open(args.output, 'a') as f:
            for url in crawler.unique_query_keys.values():
                f.write(f"{url}\n")
        print("Crawl interrupted by user. The URLs found so far have been saved.")
    except Exception as e:
        logging.exception("An unexpected error occurred during crawling")

if __name__ == "__main__":
    main()
