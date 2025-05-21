from src.spiders.base_spider import BaseJobSpider
from src.models.job import Job
from src.utils.database import SessionLocal
from typing import Dict, Any
from datetime import datetime
import json

class LinkedinSpider(BaseJobSpider):
    name = 'linkedin'
    allowed_domains = ['linkedin.com']
    
    def __init__(self, keywords=None, location=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keywords = keywords or 'senior frontend developer'
        self.location = location or 'United States'
        self.start_urls = [
            f'https://www.linkedin.com/jobs/search/?keywords={self.keywords}&location={self.location}&f_E=4&sortBy=DD'  # f_E=4 filters for senior level, DD for most recent
        ]
        self.retries = 3
        self.delay = 2  # seconds between requests
    
    def detect_frontend_stack(self, description):
        frontend_techs = {
            'frameworks': ['react', 'vue', 'angular', 'next.js', 'nuxt', 'svelte'],
            'languages': ['javascript', 'typescript', 'html', 'css'],
            'tools': ['webpack', 'vite', 'babel', 'eslint', 'jest', 'cypress'],
            'styling': ['sass', 'less', 'tailwind', 'styled-components', 'css-in-js'],
            'state': ['redux', 'mobx', 'zustand', 'recoil', 'vuex', 'pinia']
        }
        
        found_techs = {category: [] for category in frontend_techs}
        desc_lower = description.lower()
        
        for category, technologies in frontend_techs.items():
            for tech in technologies:
                if tech in desc_lower:
                    found_techs[category].append(tech)
        
        return found_techs
    
    def extract_salary_info(self, response):
        salary_text = response.css('.job-details-jobs-unified-top-card__job-insight span::text').getall()
        salary_info = {
            'min_salary': None,
            'max_salary': None,
            'currency': None,
            'salary_period': None
        }
        
        for text in salary_text:
            if any(word in text.lower() for word in ['$', '€', '£', 'salary', 'compensation']):
                # Extract numbers and try to parse salary range
                import re
                numbers = re.findall(r'[\d,]+\.?\d*', text)
                if len(numbers) >= 2:
                    salary_info['min_salary'] = float(numbers[0].replace(',', ''))
                    salary_info['max_salary'] = float(numbers[1].replace(',', ''))
                    if '$' in text:
                        salary_info['currency'] = 'USD'
                    elif '€' in text:
                        salary_info['currency'] = 'EUR'
                    elif '£' in text:
                        salary_info['currency'] = 'GBP'
                    
                    if 'year' in text.lower():
                        salary_info['period'] = 'yearly'
                    elif 'month' in text.lower():
                        salary_info['period'] = 'monthly'
                    elif 'hour' in text.lower():
                        salary_info['period'] = 'hourly'
        
        return salary_info
    
    def has_visa_sponsorship(self, description):
        visa_keywords = [
            'visa sponsorship',
            'visa sponsor',
            'will sponsor',
            'willing to sponsor',
            'h1b',
            'h-1b',
            'work permit',
            'work authorization',
            'immigration'
        ]
        return any(keyword in description.lower() for keyword in visa_keywords)
    
    def has_relocation_support(self, description):
        relocation_keywords = [
            'relocation',
            'relocation assistance',
            'relocation package',
            'relocation support',
            'moving allowance',
            'moving bonus',
            'moving assistance'
        ]
        return any(keyword in description.lower() for keyword in relocation_keywords)
    
    def parse(self, response):
        jobs = response.css('div.base-card')
        for job in jobs:
            try:
                posted_date_str = job.css('time::attr(datetime)').get()
                posted_date = datetime.fromisoformat(posted_date_str)
                
                # Validate the posted date is not in the future
                if posted_date > datetime.now():
                    self.logger.warning(f"Found job with future date: {posted_date}")
                    posted_date = datetime.now()  # Use current date as fallback
                
                job_data = {
                    'title': job.css('h3.base-search-card__title::text').get().strip(),
                    'company': job.css('h4.base-search-card__subtitle a::text').get().strip(),
                    'location': job.css('span.job-search-card__location::text').get().strip(),
                    'url': job.css('a.base-card__full-link::attr(href)').get(),
                    'source': 'LinkedIn',
                    'posted_date': posted_date
                }
                
                yield response.follow(
                    job_data['url'], 
                    self.parse_job_details,
                    cb_kwargs={'job_data': job_data}
                )
            except ValueError as e:
                self.logger.error(f"Error parsing job date: {e}")
                continue  # Skip jobs with invalid dates
            except Exception as e:
                self.logger.error(f"Error parsing job listing: {e}")
                continue
        
        # Enhanced pagination with retries
        next_page = response.css('a[aria-label="Next"]::attr(href)').get()
        if next_page:
            for _ in range(self.retries):
                try:
                    yield response.follow(
                        next_page,
                        self.parse,
                        dont_filter=True,
                        errback=self.handle_error,
                        cb_kwargs={'retry_count': 0}
                    )
                    break
                except Exception as e:
                    self.logger.error(f"Error following next page: {e}")
                    import time
                    time.sleep(self.delay)
    
    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure.value}")
        
    def parse_job_details(self, response, job_data):
        description = ' '.join(
            response.css('div.show-more-less-html__markup ::text').getall()
        ).strip()
        job_data['description'] = description
        
        # Enhanced remote detection
        remote_indicators = {
            'fully_remote': ['fully remote', '100% remote', 'remote-first'],
            'hybrid': ['hybrid', 'flexible', 'partially remote'],
            'onsite': ['on-site', 'in office', 'onsite']
        }
        
        job_data['work_type'] = 'unknown'
        desc_lower = description.lower()
        title_lower = job_data['title'].lower()
        
        for work_type, indicators in remote_indicators.items():
            if any(indicator in desc_lower or indicator in title_lower for indicator in indicators):
                job_data['work_type'] = work_type
                break
        
        # Add tech stack detection
        job_data['tech_stack'] = self.detect_frontend_stack(description)
        
        # Add salary information
        job_data.update(self.extract_salary_info(response))
        
        # Existing checks
        job_data['visa_sponsorship'] = self.has_visa_sponsorship(description)
        job_data['relocation_support'] = self.has_relocation_support(description)
        job_data['job_type'] = 'frontend'
        job_data['experience_level'] = 'senior'
        
        # Extract company info
        company_info = response.css('.jobs-company__box ::text').getall()
        job_data['company_size'] = None
        job_data['industry'] = None
        
        for info in company_info:
            if 'employees' in info.lower():
                job_data['company_size'] = info.strip()
            elif 'industry' in info.lower():
                job_data['industry'] = info.replace('Industry', '').strip()
        
        # Extract benefits
        benefits = []
        if response.css('.jobs-benefit'):
            benefits = response.css('.jobs-benefit ::text').getall()
        job_data['benefits'] = '\n'.join(benefits) if benefits else None
        
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
