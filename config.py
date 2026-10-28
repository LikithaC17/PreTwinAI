import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'pretwinshop-dev-secret-2024')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'pretwinshop.db')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    USE_LLM = bool(OPENAI_API_KEY)
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
    DEFAULT_DEMO_USER_ID = 1
    DEFAULT_BUDGET_MIN = 50.0
    DEFAULT_BUDGET_MAX = 500.0
    DEFAULT_SHOPPING_FREQUENCY = 'monthly'
    MAX_PREDICTIONS = 8
    MAX_PRODUCTS_PER_PREDICTION = 5
    MAX_COMPARISON_PRODUCTS_PER_GROUP = 4
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_ENABLED = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_AUTH_ENABLED = bool(GOOGLE_CLIENT_ID)
    # Flipkart Live Integration & Affiliate Settings
    FLIPKART_AFFILIATE_ID = os.getenv('FLIPKART_AFFILIATE_ID', '')
    FLIPKART_AFFILIATE_TOKEN = os.getenv('FLIPKART_AFFILIATE_TOKEN', '')
    FLIPKART_API_BASE_URL = os.getenv('FLIPKART_API_BASE_URL', 'https://affiliate-api.flipkart.net/affiliate/1.0')
    FLIPKART_ENABLED = os.getenv('FLIPKART_ENABLED', 'false').lower() == 'true'
    FLIPKART_CACHE_TTL_SECONDS = int(os.getenv('FLIPKART_CACHE_TTL_SECONDS', '1800'))
    FLIPKART_RATE_LIMIT_PER_MINUTE = int(os.getenv('FLIPKART_RATE_LIMIT_PER_MINUTE', '60'))
