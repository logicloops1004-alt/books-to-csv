# Books to CSV

A small Python scraper that reads the public practice catalogue at [books.toscrape.com](http://books.toscrape.com/) and writes a CSV.

The site is a sandbox made for scraping exercises. The script uses only the standard library, sends an identifiable User-Agent, and waits between pages.

## Run

```bash
python3 scrape_books.py --pages 1 --output sample_books.csv
```

## Output columns

| Column | Meaning |
| --- | --- |
| `title` | Book title |
| `price_gbp` | Listed price in pounds, without the currency symbol |
| `rating` | Star rating from 1 to 5 |
| `availability` | Stock text from the catalogue, usually `In stock` |
| `url` | Absolute link to the book page |

`sample_books.csv` is the output of one catalogue page.
