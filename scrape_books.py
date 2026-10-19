#!/usr/bin/env python3
"""Scrape book listings from books.toscrape.com into a CSV file.

books.toscrape.com is a public sandbox built for scraping practice.
The script identifies itself, pauses between pages, and writes one row
per book: title, price in GBP, star rating, availability, and URL.

Uses only the Python standard library.

Example:
    python3 scrape_books.py --pages 1 --output sample_books.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE_URL = "http://books.toscrape.com/"
USER_AGENT = (
    "BooksScraperDemo/1.0 "
    "(+https://github.com/logicloops1004-alt; practice scraper for books.toscrape.com)"
)
REQUEST_TIMEOUT_SECONDS = 20
DELAY_SECONDS = 1.0
RATINGS = {"One": "1", "Two": "2", "Three": "3", "Four": "4", "Five": "5"}
FIELDNAMES = ["title", "price_gbp", "rating", "availability", "url"]


class BookListParser(HTMLParser):
    """Collect product cards from a books.toscrape.com catalogue page.

    Closing is driven by the article end tag. Catalogue images are written
    as <img> without a matching end tag, so a depth counter would never
    return to zero.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.books: list[dict[str, str]] = []
        self._in_pod = False
        self._capture: str | None = None
        self._current: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        classes = set(attr.get("class", "").split())

        if tag == "article" and "product_pod" in classes:
            self._in_pod = True
            self._capture = None
            self._current = {"title": "", "price_gbp": "", "rating": "", "availability": "", "url": ""}
            return

        if not self._in_pod:
            return

        rating = classes & RATINGS.keys()
        if tag == "p" and rating:
            self._current["rating"] = RATINGS[next(iter(rating))]
        elif tag == "h3":
            self._capture = "title_link"
        elif tag == "a" and self._capture == "title_link":
            self._current["title"] = attr.get("title", "").strip()
            self._current["url"] = attr.get("href", "").strip()
            self._capture = None
        elif tag == "p" and "price_color" in classes:
            self._capture = "price"
            self._current["price_gbp"] = ""
        elif tag == "p" and "availability" in classes:
            self._capture = "availability"
            self._current["availability"] = ""

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "h3"} and self._capture in {"price", "availability", "title_link"}:
            self._capture = None
        if self._in_pod and tag == "article":
            if self._current.get("title"):
                self.books.append(self._current)
            self._in_pod = False
            self._capture = None
            self._current = {}

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text or not self._capture:
            return
        if self._capture == "price":
            cleaned = text.replace("£", "").replace("Â", "").strip()
            self._current["price_gbp"] = f"{self._current['price_gbp']} {cleaned}".strip()
        elif self._capture == "availability":
            self._current["availability"] = f"{self._current['availability']} {text}".strip()


def page_url(page: int) -> str:
    if page <= 1:
        return urljoin(BASE_URL, "index.html")
    return urljoin(BASE_URL, f"catalogue/page-{page}.html")


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def scrape_page(page: int) -> list[dict[str, str]]:
    url = page_url(page)
    parser = BookListParser()
    parser.feed(fetch(url))
    books = []
    for book in parser.books:
        book["url"] = urljoin(url, book["url"])
        books.append(book)
    return books


def write_csv(path: str, books: list[dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(books)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape books.toscrape.com into a CSV file.")
    parser.add_argument("--pages", type=int, default=1, help="Number of catalogue pages to fetch (default: 1).")
    parser.add_argument("--output", default="sample_books.csv", help="CSV path to write (default: sample_books.csv).")
    parser.add_argument("--delay", type=float, default=DELAY_SECONDS, help="Seconds to wait between pages (default: 1).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.pages < 1:
        print("error: --pages must be at least 1", file=sys.stderr)
        return 2
    if args.delay < 0:
        print("error: --delay must be 0 or greater", file=sys.stderr)
        return 2

    books: list[dict[str, str]] = []
    for page in range(1, args.pages + 1):
        if page > 1 and args.delay:
            time.sleep(args.delay)
        url = page_url(page)
        try:
            page_books = scrape_page(page)
        except HTTPError as exc:
            print(f"error: HTTP {exc.code} for {url}", file=sys.stderr)
            return 1
        except URLError as exc:
            print(f"error: could not reach {url}: {exc.reason}", file=sys.stderr)
            return 1
        if not page_books:
            print(f"error: no books found on {url}", file=sys.stderr)
            return 1
        books.extend(page_books)
        print(f"fetched {len(page_books)} books from {url}")

    write_csv(args.output, books)
    print(f"wrote {len(books)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
