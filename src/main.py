from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from src.utils.database import init_db, SessionLocal, engine
from src.models.job import Job, Base
from src.spiders.linkedin import LinkedinSpider
from src.spiders.jobinja import JobinjaSpider
from src.spiders.jobvision import JobvisionSpider
from src.utils.telegram_bot import JobTelegramBot
import logging
import argparse
from datetime import datetime, timedelta
import json
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def format_salary(job):
    if not job.min_salary and not job.max_salary:
        return "Not specified"
    
    salary_range = []
    if job.min_salary:
        salary_range.append(f"{job.currency} {job.min_salary:,.0f}")
    if job.max_salary:
        salary_range.append(f"{job.currency} {job.max_salary:,.0f}")
    
    salary_str = " - ".join(salary_range)
    if job.salary_period:
        salary_str += f" per {job.salary_period}"
    
    return salary_str

def format_tech_stack(tech_stack):
    if not tech_stack:
        return "Not specified"
    
    result = []
    for category, techs in tech_stack.items():
        if techs:
            result.append(f"{category.title()}: {', '.join(techs)}")
    
    return "\n".join(result) if result else "Not specified"

def display_results(args):
    db = SessionLocal()
    try:
        query = db.query(Job)
        
        if args.visa_only:
            query = query.filter(Job.visa_sponsorship == True)
        if args.relocation_only:
            query = query.filter(Job.relocation_support == True)
        if args.days:
            cutoff_date = datetime.now() - timedelta(days=args.days)
            query = query.filter(Job.posted_date >= cutoff_date)
            
        jobs = query.all()
        
        print("\n=== Job Search Results ===\n")
        if args.days:
            print(f"Showing jobs posted in the last {args.days} days\n")
            
        for job in jobs:
            print(f"Title: {job.title}")
            print(f"Company: {job.company}")
            print(f"Location: {job.location}")
            print(f"Work Type: {job.work_type.replace('_', ' ').title() if job.work_type else 'Not specified'}")
            print(f"Industry: {job.industry or 'Not specified'}")
            print(f"Company Size: {job.company_size or 'Not specified'}")
            print(f"\nCompensation: {format_salary(job)}")
            print(f"\nTechnology Stack:\n{format_tech_stack(job.tech_stack)}")
            print(f"\nVisa Sponsorship: {'Yes' if job.visa_sponsorship else 'Not mentioned'}")
            print(f"Relocation Support: {'Yes' if job.relocation_support else 'Not mentioned'}")
            
            if job.benefits:
                print(f"\nBenefits: {job.benefits}")
            
            if job.posted_date:
                print(f"\nPosted: {job.posted_date.strftime('%Y-%m-%d')}")
                
            print(f"\nURL: {job.url}")
            print("=" * 80 + "\n")
            
        print(f"Total jobs found: {len(jobs)}")
        
        # Print some analytics
        visa_count = sum(1 for job in jobs if job.visa_sponsorship)
        relocation_count = sum(1 for job in jobs if job.relocation_support)
        remote_count = sum(1 for job in jobs if job.work_type == 'fully_remote')
        
        print("\nQuick Stats:")
        print(f"- Jobs with visa sponsorship: {visa_count}")
        print(f"- Jobs with relocation support: {relocation_count}")
        print(f"- Fully remote positions: {remote_count}")
        
    finally:
        db.close()

def get_input_with_default(prompt, default):
    user_input = input(f"{prompt} (default: {default}): ").strip()
    return user_input if user_input else default

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Job Scraper')
    parser.add_argument('--spider', type=str, default='linkedin',
                      help='Spider to run (default: linkedin, options: linkedin, jobinja, jobvision)')
    parser.add_argument('--keywords', type=str,
                      help='Job keywords to search for')
    parser.add_argument('--location', type=str,
                      help='Job location to search in')
    parser.add_argument('--visa-only', action='store_true',
                      help='Only show jobs with visa sponsorship')
    parser.add_argument('--relocation-only', action='store_true',
                      help='Only show jobs with relocation support')
    parser.add_argument('--reset-db', action='store_true',
                      help='Reset the database before scraping')
    parser.add_argument('--days', type=int,
                      help='Only show jobs posted within the last N days')
    parser.add_argument('--no-telegram', action='store_true',
                      help='Disable Telegram notifications')
    
    args = parser.parse_args()
    
    # Initialize Telegram bot if enabled
    telegram_bot = None
    if not args.no_telegram and os.getenv('TELEGRAM_BOT_TOKEN'):
        try:
            telegram_bot = JobTelegramBot()
            await telegram_bot.start_bot()
            logger.info("Telegram bot started successfully")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            telegram_bot = None
    
    # Interactively ask for position and location if not provided
    if not args.keywords:
        args.keywords = get_input_with_default(
            "Enter job position",
            "senior frontend developer"
        )
    
    if not args.location:
        args.location = get_input_with_default(
            "Enter location",
            "United States"
        )
    
    # Reset database if requested
    if args.reset_db:
        logger.info("Resetting database...")
        Base.metadata.drop_all(bind=engine)
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Get Scrapy settings
    settings = get_project_settings()
    settings.update({
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 2,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    # Initialize crawler process
    process = CrawlerProcess(settings)
    
    # Add spider based on argument
    spider_class = None
    if args.spider.lower() == 'linkedin':
        spider_class = LinkedinSpider
    elif args.spider.lower() == 'jobinja':
        spider_class = JobinjaSpider
    elif args.spider.lower() == 'jobvision':
        spider_class = JobvisionSpider
    else:
        logger.error(f"Spider '{args.spider}' not found")
        return

    # Create spider instance with telegram bot
    spider = spider_class(
        keywords=args.keywords,
        location=args.location
    )
    if telegram_bot:
        spider.telegram_bot = telegram_bot

    process.crawl(spider)
    
    logger.info(f"Starting {args.spider} spider...")
    logger.info(f"Searching for: {args.keywords} in {args.location}")
    process.start()
    
    # Display results
    display_results(args)

    # Stop the Telegram bot
    if telegram_bot:
        await telegram_bot.stop_bot()

if __name__ == "__main__":
    asyncio.run(main())
