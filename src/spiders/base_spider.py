from scrapy import Spider
from typing import Dict, Any, List

class BaseJobSpider(Spider):
    name = 'base_job_spider'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jobs: List[Dict[str, Any]] = []
    
    def parse(self, response):
        """
        Base parse method to be implemented by child classes
        """
        raise NotImplementedError
    
    def parse_job_details(self, response):
        """
        Base method to parse individual job details
        To be implemented by child classes
        """
        raise NotImplementedError
