# Job Scraper

A Python-based job scraping application that collects job listings from various job boards using Scrapy.

## Features

- Scrapes job listings from various job boards
- Stores data in SQLite database (configurable to use other databases)
- Modular spider design for easy addition of new job sources
- Handles pagination and detailed job information
- Automatic detection of remote positions

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python -c "from src.utils.database import init_db; init_db()"
```

## Usage

To run the LinkedIn job scraper:

```bash
python src/main.py
```

## Project Structure

```
.
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── settings.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── job.py
│   ├── spiders/
│   │   ├── __init__.py
│   │   ├── base_spider.py
│   │   └── linkedin.py
│   └── utils/
│       ├── __init__.py
│       └── database.py
```

## Configuration

- Adjust scraping settings in `src/settings.py`
- Configure database connection in `.env` file (create one if it doesn't exist)
- Customize spider behavior in individual spider files

## Adding New Job Sources

1. Create a new spider in `src/spiders/`
2. Inherit from `BaseJobSpider`
3. Implement the required parse methods
4. Add the spider to `main.py`
