from setuptools import setup, find_packages

setup(
    name="job-scraper",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'scrapy>=2.13.0',
        'sqlalchemy>=2.0.41',
        'beautifulsoup4>=4.13.4',
        'python-dotenv>=1.0.0',
    ],
)
