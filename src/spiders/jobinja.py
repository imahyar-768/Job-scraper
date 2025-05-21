from src.spiders.base_spider import BaseJobSpider
from src.models.job import Job
from src.utils.database import SessionLocal
from typing import Dict, Any
from datetime import datetime, timedelta
import json
import re
import urllib.parse
from scrapy.http import Request
import logging
import asyncio

class JobinjaSpider(BaseJobSpider):
    name = 'jobinja'
    allowed_domains = ['jobinja.ir']
    
    def __init__(self, keywords=None, location=None, max_pages=10, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keywords = keywords or 'برنامه نویس'
        self.location = location or 'تهران'
        self.max_pages = int(max_pages)
        self.current_page = 1
        
        # Format keywords and location for URL - new format
        encoded_keywords = urllib.parse.quote(self.keywords)
        encoded_location = urllib.parse.quote(self.location)
        self.start_urls = [
            f'https://jobinja.ir/jobs?&filters[locations][0]={encoded_location}&q={encoded_keywords}'
        ]
        self.retries = 3
        self.delay = 2
        self.logger.setLevel(logging.DEBUG)
        
    def start_requests(self):
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://jobinja.ir/'
        }
        
        cookies = {
            'locale': 'fa',
            'country': 'IR'
        }
        
        for url in self.start_urls:
            yield Request(
                url=url,
                headers=headers,
                cookies=cookies,
                callback=self.parse,
                dont_filter=True,
                meta={
                    'dont_redirect': False,  # Allow redirects
                    'handle_httpstatus_list': [301, 302],
                    'download_timeout': 30
                }
            )

    def parse_persian_date(self, date_str):
        """Convert Persian date text to datetime object"""
        if not date_str:
            return datetime.now()
            
        try:
            # Strip any extra whitespace and parentheses
            date_str = date_str.strip('() \n\t')
            
            # Handle relative dates
            if 'روز پیش' in date_str:
                days = int(''.join(filter(str.isdigit, date_str)))
                return datetime.now() - timedelta(days=days)
            elif 'ساعت پیش' in date_str:
                hours = int(''.join(filter(str.isdigit, date_str)))
                return datetime.now() - timedelta(hours=hours)
            elif 'هفته پیش' in date_str:
                weeks = int(''.join(filter(str.isdigit, date_str)))
                return datetime.now() - timedelta(weeks=weeks)
            elif 'ماه پیش' in date_str:
                months = int(''.join(filter(str.isdigit, date_str)))
                return datetime.now() - timedelta(days=months*30)
            elif 'دقیقه پیش' in date_str:
                minutes = int(''.join(filter(str.isdigit, date_str)))
                return datetime.now() - timedelta(minutes=minutes)
            elif 'امروز' in date_str:
                return datetime.now()
            else:
                return datetime.now()
        except Exception as e:
            self.logger.error(f"Error parsing Persian date '{date_str}': {e}")
            return datetime.now()

    def parse(self, response):
        self.logger.debug(f"Parsing page: {response.url}")
        self.logger.debug(f"Response status: {response.status}")

        # Extract job listings
        job_items = response.css('div.o-listView__itemWrap.c-jobListView__itemWrap')
        self.logger.debug(f"Found {len(job_items)} job listings")

        if not job_items:
            self.logger.error("No jobs found with any selector")
            self.logger.debug("Page content preview:")
            self.logger.debug(response.css('body').get()[:1000])
            return

        for job_item in job_items:
            try:
                # Get the job info container
                info_container = job_item.css('div.o-listView__itemInfo')
                
                # Extract basic job information with error checking
                title_element = info_container.css('h2.o-listView__itemTitle a.c-jobListView__titleLink')
                if not title_element:
                    continue
                    
                title = title_element.css('::text').get('').strip()
                url = title_element.css('::attr(href)').get('')

                if not (title and url):
                    continue

                # Extract company name
                company = info_container.css('span:contains("‌")::text, .c-jobListView__metaItem span::text').get('').strip()
                
                # Extract location
                location = info_container.css('.c-jobListView__metaItem span::text').getall()
                location = next((loc.strip() for loc in location if 'تهران' in loc or 'مشهد' in loc), 'تهران')
                
                # Extract posted date
                date_span = info_container.css('span.c-jobListView__passedDays::text').get()
                posted_date = self.parse_persian_date(date_span)

                job_data = {
                    'title': title,
                    'company': company,
                    'location': location,
                    'url': response.urljoin(url),
                    'source': 'Jobinja',
                    'posted_date': posted_date
                }

                self.logger.info(f"Successfully parsed job: {job_data['title']} at {job_data['company']}")
                
                yield response.follow(
                    url=job_data['url'],
                    callback=self.parse_job_details,
                    cb_kwargs={'job_data': job_data},
                    errback=self.handle_error
                )

            except Exception as e:
                self.logger.error(f"Error parsing job listing: {str(e)}")
                self.logger.debug(f"Problem job HTML: {job_item.get()}")
                continue

        # Handle pagination
        next_page_url = response.css('a.c-pagination__next::attr(href), a[rel="next"]::attr(href)').get()
        
        if next_page_url and self.current_page < self.max_pages:
            self.current_page += 1
            self.logger.debug(f"Following next page: {next_page_url} (Page {self.current_page} of {self.max_pages})")
            yield response.follow(
                url=next_page_url,
                callback=self.parse,
                errback=self.handle_error
            )
        else:
            self.logger.info(f"Reached maximum page limit ({self.max_pages})")

    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure.value}")

    def parse_job_details(self, response, job_data):
        try:
            self.logger.debug(f"Parsing job details from {response.url}")

            # Extract job description
            description_texts = []
            description_selectors = [
                'div.o-box__text::text',
                'div.o-box__text p::text',
                'div.s-jobDesc::text',
                'div.s-jobDesc p::text',
                '.c-jobView__description *::text',
                '.o-box.c-jobView__section *::text'
            ]
            
            for selector in description_selectors:
                texts = response.css(selector).getall()
                if texts:
                    description_texts.extend(texts)
            
            description = ' '.join(text.strip() for text in description_texts if text.strip())
            
            if not description:
                self.logger.warning(f"No description found for job at {response.url}")
                description = "توضیحات در دسترس نیست"

            # Extract additional metadata
            metadata = {
                'employment_type': response.css('div.c-jobView__metaItem:contains("نوع همکاری") span::text').get('').strip(),
                'experience': response.css('div.c-jobView__metaItem:contains("سابقه") span::text').get('').strip(),
                'education': response.css('div.c-jobView__metaItem:contains("تحصیلات") span::text').get('').strip(),
                'category': response.css('div.c-jobView__metaItem:contains("دسته‌بندی") a::text').get('').strip(),
                'salary': self.extract_salary_range(response),
                'tech_stack': self.detect_tech_stack(description)
            }

            # Update job data with new information
            job_data.update({
                'description': description,
                'metadata': metadata
            })

            # Create and save job instance
            db = SessionLocal()
            try:
                job = Job(
                    title=job_data['title'],
                    company=job_data['company'],
                    location=job_data['location'],
                    description=job_data['description'],
                    url=job_data['url'],
                    source=job_data['source'],
                    posted_date=job_data['posted_date'],
                    metadata=json.dumps(metadata, ensure_ascii=False)
                )
                db.add(job)
                db.commit()
                self.logger.info(f"Successfully saved job: {job.title}")

                # Send Telegram notification if bot is available
                if hasattr(self, 'telegram_bot'):
                    asyncio.create_task(self.telegram_bot.send_job_notification(job_data))

            except Exception as e:
                self.logger.error(f"Database error: {str(e)}")
                db.rollback()
            finally:
                db.close()

            return job_data

        except Exception as e:
            self.logger.error(f"Error parsing job details: {str(e)}")
            return job_data

    def detect_tech_stack(self, text):
        """Detect technologies mentioned in the job description"""
        tech_keywords = {
            'python': ['python', 'django', 'flask', 'fastapi', 'پایتون'],
            'javascript': ['javascript', 'جاوااسکریپت', 'js', 'node', 'react', 'vue', 'angular'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch'],
            'cloud': ['aws', 'azure', 'docker', 'kubernetes', 'k8s'],
            'other': ['git', 'rest', 'api', 'linux', 'ci/cd', 'jenkins']
        }
        
        found_tech = set()
        text_lower = text.lower()
        
        for category, terms in tech_keywords.items():
            for term in terms:
                if term.lower() in text_lower:
                    found_tech.add(term)
        
        return list(found_tech)

    def extract_salary_range(self, response):
        """Extract salary information if available"""
        salary_selectors = [
            'div.c-jobView__metaItem:contains("حقوق") span::text',
            'div:contains("حقوق") span.black::text',
            '.c-jobView__metaItem--salaryType span::text'
        ]
        
        for selector in salary_selectors:
            salary = response.css(selector).get()
            if salary:
                return salary.strip()
        return None

    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure.value}")
        if hasattr(failure.value, 'response'):
            self.logger.error(f"Response status: {failure.value.response.status}")
            self.logger.error(f"Response headers: {failure.value.response.headers}")

    def detect_tech_stack(self, description):
        tech_categories = {
            'frameworks': ['django', 'flask', 'fastapi', 'laravel', 'spring', 'react', 'vue', 'angular'],
            'languages': ['python', 'php', 'java', 'javascript', 'typescript', 'go', 'rust'],
            'databases': ['mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch'],
            'tools': ['docker', 'kubernetes', 'git', 'linux', 'aws', 'azure']
        }
        
        found_techs = {category: [] for category in tech_categories}
        desc_lower = description.lower()
        
        for category, technologies in tech_categories.items():
            for tech in technologies:
                if tech in desc_lower:
                    found_techs[category].append(tech)
        
        return found_techs

    def extract_salary_info(self, salary_texts):
        salary_info = {
            'min_salary': None,
            'max_salary': None,
            'currency': 'IRR',
            'salary_period': 'monthly'
        }
        
        if not salary_texts:
            return salary_info
            
        salary_text = ' '.join(salary_texts)
        numbers = re.findall(r'[\d,]+', salary_text)
        
        if len(numbers) >= 2:
            try:
                salary_info['min_salary'] = float(numbers[0].replace(',', ''))
                salary_info['max_salary'] = float(numbers[1].replace(',', ''))
            except (ValueError, IndexError):
                pass
        
        return salary_info
