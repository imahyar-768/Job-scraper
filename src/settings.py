# Scrapy settings
BOT_NAME = 'jobscraper'

SPIDER_MODULES = ['src.spiders']
NEWSPIDER_MODULE = 'src.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performing at the same time
CONCURRENT_REQUESTS = 1

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True

# Enable cookies
COOKIES_ENABLED = True
COOKIES_DEBUG = True

# Handle redirects
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 5

# Configure retries
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 404, 403]

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 500,
    'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 700,
}

# Configure item pipelines
ITEM_PIPELINES = {
    # Add your pipelines here
}

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# Additional settings for handling Persian sites
FEED_EXPORT_ENCODING = 'utf-8'
SCHEDULER_PRIORITY_QUEUE = 'scrapy.pqueues.DownloaderAwarePriorityQueue'
REACTOR_THREADPOOL_MAXSIZE = 20

# Increase timeouts
DOWNLOAD_TIMEOUT = 30
AJAXCRAWL_ENABLED = True
