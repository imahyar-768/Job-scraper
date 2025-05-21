from src.spiders.base_spider import BaseJobSpider
from src.models.job import Job
from src.utils.database import SessionLocal
from typing import Dict, Any
from datetime import datetime, timedelta
import json
import re

class JobvisionSpider(BaseJobSpider):
    name = 'jobvision'
    allowed_domains = ['jobvision.ir']
    
    def __init__(self, keywords=None, location=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keywords = keywords or 'برنامه نویس'
        self.location = location or 'تهران'
        self.start_urls = [
            f'https://jobvision.ir/jobs?keyword={self.keywords}&city={self.location}'
        ]
        self.retries = 3
        self.delay = 2

    def parse_persian_date(self, date_str):
        """Convert Persian date text to datetime object"""
        try:
            # Handle relative dates
            if 'روز پیش' in date_str:
                days = int(re.search(r'\d+', date_str).group())
                return datetime.now() - timedelta(days=days)
            elif 'ساعت پیش' in date_str:
                hours = int(re.search(r'\d+', date_str).group())
                return datetime.now() - timedelta(hours=hours)
            elif 'هفته پیش' in date_str:
                weeks = int(re.search(r'\d+', date_str).group())
                return datetime.now() - timedelta(weeks=weeks)
            else:
                return datetime.now()  # fallback to current date
        except Exception as e:
            self.logger.error(f"Error parsing Persian date: {e}")
            return datetime.now()

    def parse(self, response):
        jobs = response.css('div.job-card')
        for job in jobs:
            try:
                posted_date_str = job.css('span.job-card__date::text').get()
                posted_date = self.parse_persian_date(posted_date_str)
                
                job_data = {
                    'title': job.css('h2.job-card__title::text').get().strip(),
                    'company': job.css('span.job-card__company::text').get().strip(),
                    'location': job.css('span.job-card__location::text').get().strip(),
                    'url': response.urljoin(job.css('a.job-card__link::attr(href)').get()),
                    'source': 'Jobvision',
                    'posted_date': posted_date
                }
                
                yield response.follow(
                    job_data['url'],
                    self.parse_job_details,
                    cb_kwargs={'job_data': job_data}
                )
            except Exception as e:
                self.logger.error(f"Error parsing job listing: {e}")
                continue

        # Handle pagination
        next_page = response.css('a.pagination__next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_job_details(self, response, job_data):
        description = ' '.join(
            response.css('div.job-detail__description ::text').getall()
        ).strip()
        job_data['description'] = description
        
        # Extract salary information
        salary_elem = response.css('div.job-detail__salary ::text').getall()
        salary_info = self.extract_salary_info(salary_elem)
        job_data.update(salary_info)
        
        # Extract tech stack
        job_data['tech_stack'] = self.detect_tech_stack(description)
        
        # Work type detection
        work_types = {
            'fully_remote': ['دورکاری', 'ریموت'],
            'hybrid': ['هیبرید', 'ترکیبی'],
            'onsite': ['حضوری']
        }
        
        job_data['work_type'] = 'unknown'
        desc_lower = description.lower()
        
        for work_type, indicators in work_types.items():
            if any(indicator in desc_lower for indicator in indicators):
                job_data['work_type'] = work_type
                break
        
        # Extract additional info
        company_info = response.css('div.company-info__details ::text').getall()
        job_data['company_size'] = None
        job_data['industry'] = None
        
        for info in company_info:
            if 'نفر' in info:
                job_data['company_size'] = info.strip()
            elif 'صنعت' in info:
                job_data['industry'] = info.replace('صنعت:', '').strip()
        
        # Store in database
        db = SessionLocal()
        try:
            job = Job(**job_data)
            db.add(job)
            db.commit()
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error saving job: {e}")
        finally:
            db.close()
        
        return job_data

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
