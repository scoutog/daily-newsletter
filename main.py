import os
import smtplib
import schedule
import time
import csv
import base64
import io
import random
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# Load environment variables
load_dotenv()

# Configuration from environment variables
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
COUNTRY_CODE = os.getenv('COUNTRY_CODE', 'US')  # Default country code

# Email configuration
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # App password for Gmail
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))

# CSV file path
EMAIL_LIST_CSV = os.getenv('EMAIL_LIST_CSV', 'email-list.csv')

# XKCD state file to track last shown comic
XKCD_STATE_FILE = 'last_xkcd_shown.txt'

# State name to state code mapping
STATE_MAPPING = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'District of Columbia': 'DC'
}


def get_state_code(state_name):
    """Convert state name to state code"""
    if not state_name:
        return None
    # Check if it's already a code (2 letters)
    if len(state_name) == 2 and state_name.isupper():
        return state_name
    # Try to map state name to code
    return STATE_MAPPING.get(state_name, state_name)


def get_weather_data(city, state=None, zip_code=None):
    """Fetch current weather and hourly forecast from OpenWeatherMap API"""
    try:
        # Build query string - prefer zip code, then city+state, then just city
        if zip_code:
            query = f"zip={zip_code},{COUNTRY_CODE}"
        elif state:
            state_code = get_state_code(state)
            query = f"q={city},{state_code},{COUNTRY_CODE}"
        else:
            query = f"q={city},{COUNTRY_CODE}"
        
        # Get current weather
        current_url = f"http://api.openweathermap.org/data/2.5/weather?{query}&appid={WEATHER_API_KEY}&units=imperial"
        current_response = requests.get(current_url)
        current_response.raise_for_status()
        current_data = current_response.json()
        
        # Get coordinates for forecast
        lat = current_data['coord']['lat']
        lon = current_data['coord']['lon']
        
        # Try to use One Call API 3.0 for hourly forecasts (requires subscription)
        # Fall back to 5-day/3-hour forecast if One Call API is not available
        try:
            onecall_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,daily,alerts&appid={WEATHER_API_KEY}&units=imperial"
            onecall_response = requests.get(onecall_url)
            if onecall_response.status_code == 200:
                onecall_data = onecall_response.json()
                # Return current data with hourly forecast in compatible format
                return current_data, {'list': onecall_data.get('hourly', [])}
        except:
            pass
        
        # Fallback: Use 5-day/3-hour forecast API
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=imperial&cnt=40"
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        
        return current_data, forecast_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data for {city}, {state}: {e}")
        return None, None


def get_moon_phase():
    """Calculate current moon phase and return phase name and emoji"""
    # Known new moon date (Jan 11, 2024)
    known_new_moon = datetime(2024, 1, 11, 11, 57)
    
    # Lunar cycle is approximately 29.53 days
    lunar_cycle = 29.53058867
    
    # Calculate days since known new moon
    now = datetime.now()
    days_since = (now - known_new_moon).total_seconds() / 86400
    
    # Calculate current position in lunar cycle (0-29.53)
    phase_position = days_since % lunar_cycle
    
    # Determine phase name and emoji
    if phase_position < 1.84566:
        return "New Moon", "🌑"
    elif phase_position < 7.38264:
        return "Waxing Crescent", "🌒"
    elif phase_position < 9.22831:
        return "First Quarter", "🌓"
    elif phase_position < 14.76529:
        return "Waxing Gibbous", "🌔"
    elif phase_position < 16.61096:
        return "Full Moon", "🌕"
    elif phase_position < 22.14794:
        return "Waning Gibbous", "🌖"
    elif phase_position < 23.99361:
        return "Last Quarter", "🌗"
    else:
        return "Waning Crescent", "🌘"


def get_historical_fact():
    """Fetch historical event that happened on this day using Wikipedia's On This Day API"""
    try:
        now = datetime.now()
        month = str(now.month).zfill(2)  # Pad with zero
        day = str(now.day).zfill(2)  # Pad with zero
        
        # Wikipedia REST API endpoint (different format)
        url = f'https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}'
        
        headers = {
            'User-Agent': 'DailyBriefEmailApp/1.0 (Contact: scout3303@gmail.com)'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Get events from history
        events = data.get('events', [])
        
        if events:
            # Filter events with good descriptions
            valid_events = [e for e in events if e.get('text') and e.get('year') and len(e.get('text', '')) > 20]
            
            if valid_events:
                # Pick a random event
                event = random.choice(valid_events)
            else:
                # Fallback to any event
                event = random.choice(events)
            
            year = event.get('year', '')
            text = event.get('text', '')
            
            # Get Wikipedia URL if available
            wiki_url = ''
            if event.get('pages') and len(event['pages']) > 0:
                wiki_url = event['pages'][0].get('content_urls', {}).get('desktop', {}).get('page', '')
            
            return {
                'year': year,
                'text': text,
                'url': wiki_url
            }
        
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching historical fact: {e}")
        return None
    except Exception as e:
        print(f"Error processing historical fact: {e}")
        return None


def get_stock_market_data():
    """Fetch S&P 500 data using Yahoo Finance API"""
    try:
        # Using Yahoo Finance API for S&P 500 (^GSPC)
        url = 'https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=2d'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Get the latest price and previous close
        result = data.get('chart', {}).get('result', [{}])[0]
        meta = result.get('meta', {})
        
        # Get current price (regularMarketPrice during hours, chartPreviousClose after)
        current_price = meta.get('regularMarketPrice', 0)
        # chartPreviousClose is the previous day's close
        previous_close = meta.get('chartPreviousClose', 0)
        
        # If we have price data
        if current_price and previous_close:
            change = current_price - previous_close
            percent_change = (change / previous_close) * 100
            
            return {
                'price': round(current_price, 2),
                'change': round(change, 2),
                'percent_change': round(percent_change, 2),
                'is_positive': change >= 0
            }
        
        return None
    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return None


def get_movie_recommendation():
    """Fetch a movie recommendation from The Movie Database (TMDB) API"""
    if not TMDB_API_KEY:
        print("Warning: TMDB_API_KEY not set. Skipping movie recommendation.")
        return None
    
    try:
        # Get top-rated movies (quality over recency)
        # Use a random page to get variety (pages 1-10 cover ~200 top-rated movies)
        random_page = random.randint(1, 10)
        url = f'https://api.themoviedb.org/3/movie/top_rated?api_key={TMDB_API_KEY}&page={random_page}'
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        movies = data.get('results', [])
        
        if movies:
            # Pick a random movie from the page
            movie = random.choice(movies)
            
            # Get movie details for more information
            movie_id = movie.get('id')
            details_url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}'
            details_response = requests.get(details_url, timeout=10)
            details_response.raise_for_status()
            details = details_response.json()
            
            # Build poster URL
            poster_path = movie.get('poster_path', '')
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ''
            
            # Get genres
            genres = [g.get('name') for g in details.get('genres', [])]
            genre_str = ', '.join(genres[:3]) if genres else 'N/A'
            
            # Get runtime
            runtime = details.get('runtime', 0)
            runtime_str = f"{runtime} min" if runtime else 'N/A'
            
            # Get rating
            rating = movie.get('vote_average', 0)
            
            return {
                'title': movie.get('title', 'Unknown'),
                'overview': movie.get('overview', 'No overview available.'),
                'poster_url': poster_url,
                'release_date': movie.get('release_date', 'N/A'),
                'rating': round(rating, 1),
                'genres': genre_str,
                'runtime': runtime_str,
                'tmdb_url': f"https://www.themoviedb.org/movie/{movie_id}"
            }
        
        return None
    except Exception as e:
        print(f"Error fetching movie recommendation: {e}")
        return None


def get_xkcd_comic():
    """Fetch XKCD comic - latest if published today/yesterday and not yet shown, otherwise random"""
    try:
        # First, fetch the latest comic to check if it's new
        latest_url = 'https://xkcd.com/info.0.json'
        
        response = requests.get(latest_url, timeout=10)
        response.raise_for_status()
        latest_data = response.json()
        
        # Check if the latest comic was published today or yesterday
        # This catches comics published either:
        # - Yesterday afternoon/evening (show the next morning)
        # - Today early morning before 8am (show this morning)
        comic_year = latest_data.get('year')
        comic_month = latest_data.get('month')
        comic_day = latest_data.get('day')
        comic_num = latest_data.get('num')
        
        # Create date object for the comic's publication date
        comic_date = datetime(int(comic_year), int(comic_month), int(comic_day)).date()
        today = datetime.now().date()
        yesterday = (datetime.now() - timedelta(days=1)).date()
        
        # Check if comic is from today or yesterday
        is_recent = (comic_date == today) or (comic_date == yesterday)
        
        # Read the last shown comic number from state file
        last_shown_num = None
        try:
            if os.path.exists(XKCD_STATE_FILE):
                with open(XKCD_STATE_FILE, 'r') as f:
                    last_shown_num = int(f.read().strip())
        except:
            pass
        
        # Show the latest comic if it's recent AND we haven't shown it before
        if is_recent and comic_num != last_shown_num:
            # Save this comic number to state file so we don't show it again
            try:
                with open(XKCD_STATE_FILE, 'w') as f:
                    f.write(str(comic_num))
            except Exception as e:
                print(f"Warning: Could not save xkcd state: {e}")
            
            # Show the new comic
            return {
                'title': latest_data.get('title', ''),
                'img': latest_data.get('img', ''),
                'alt': latest_data.get('alt', ''),
                'num': comic_num,
                'link': f"https://xkcd.com/{comic_num}",
                'is_new': True,
                'label': f"New comic #{comic_num}"
            }
        else:
            # No new comic to show, fetch a random one
            max_comic_num = latest_data.get('num', 2000)
            random_num = random.randint(1, max_comic_num)
            
            # Fetch the random comic
            random_url = f'https://xkcd.com/{random_num}/info.0.json'
            random_response = requests.get(random_url, timeout=10)
            random_response.raise_for_status()
            random_data = random_response.json()
            
            return {
                'title': random_data.get('title', ''),
                'img': random_data.get('img', ''),
                'alt': random_data.get('alt', ''),
                'num': random_data.get('num', ''),
                'link': f"https://xkcd.com/{random_data.get('num', '')}",
                'is_new': False,
                'label': f"No new comic, here's a random one #{random_data.get('num', '')}"
            }
            
    except Exception as e:
        print(f"Error fetching XKCD comic: {e}")
        return None


def get_top_news_stories(num_stories=8):
    """Fetch top news stories and big USA headlines using NewsAPI"""
    if not NEWS_API_KEY:
        print("Warning: NEWS_API_KEY not set. Skipping news section.")
        return []
    
    try:
        # Use top-headlines endpoint without 'from' parameter to get the biggest current headlines
        # Request more articles than needed so we can filter and prioritize
        url = f'https://newsapi.org/v2/top-headlines?country=us&pageSize={num_stories * 2}&apiKey={NEWS_API_KEY}'
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        articles = data.get('articles', [])
        
        # Filter out articles without title, url, or description
        # Also filter out removed articles and those without meaningful content
        filtered_articles = []
        for article in articles:
            title = article.get('title', '')
            url = article.get('url', '')
            description = article.get('description', '')
            
            # Skip if missing key information or marked as removed
            if not title or not url or title == '[Removed]':
                continue
            
            # Skip horoscope articles
            if 'horoscope' in title.lower():
                continue
            
            # Skip if description is too short (likely not a major story)
            if description and len(description) < 30:
                continue
                
            filtered_articles.append(article)
        
        # Also fetch "everything" endpoint for breaking news to supplement
        # This helps catch major stories that might not be in top-headlines yet
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            everything_url = f'https://newsapi.org/v2/everything?q=USA OR "United States" OR breaking&language=en&sortBy=popularity&from={today}&pageSize=10&apiKey={NEWS_API_KEY}'
            
            everything_response = requests.get(everything_url, timeout=10)
            if everything_response.status_code == 200:
                everything_data = everything_response.json()
                everything_articles = everything_data.get('articles', [])
                
                # Add articles from everything endpoint that aren't already included
                existing_urls = {a.get('url') for a in filtered_articles}
                for article in everything_articles:
                    if article.get('url') not in existing_urls and article.get('title') and article.get('title') != '[Removed]':
                        filtered_articles.append(article)
        except Exception as e:
            print(f"Note: Could not fetch supplementary news: {e}")
        
        # Return top stories up to the requested number
        return filtered_articles[:num_stories]
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return []
    except Exception as e:
        print(f"Error processing news: {e}")
        return []


def interpolate_to_hourly(forecasts, start_time, end_time):
    """Interpolate 3-hourly forecasts to create 2-hourly entries"""
    hourly_forecasts = []
    
    # Create a list of 2-hour intervals from start to end
    current_hour = start_time.replace(minute=0, second=0, microsecond=0)
    
    while current_hour <= end_time:
        current_timestamp = current_hour.timestamp()
        
        # Find the closest forecast points for interpolation
        before_forecast = None
        after_forecast = None
        
        for i, forecast in enumerate(forecasts):
            if forecast['dt'] <= current_timestamp:
                before_forecast = forecast
                if i + 1 < len(forecasts):
                    after_forecast = forecasts[i + 1]
            elif forecast['dt'] > current_timestamp:
                if before_forecast is None:
                    before_forecast = forecast
                after_forecast = forecast
                break
        
        # If we have both before and after, interpolate
        if before_forecast and after_forecast:
            # Calculate interpolation factor (0 to 1)
            time_diff = after_forecast['dt'] - before_forecast['dt']
            if time_diff > 0:
                factor = (current_timestamp - before_forecast['dt']) / time_diff
                
                # Interpolate temperature
                temp_before = before_forecast['main']['temp']
                temp_after = after_forecast['main']['temp']
                interpolated_temp = temp_before + (temp_after - temp_before) * factor
                
                # Interpolate feels like
                feels_before = before_forecast['main']['feels_like']
                feels_after = after_forecast['main']['feels_like']
                interpolated_feels = feels_before + (feels_after - feels_before) * factor
                
                # Use the closer forecast's weather condition
                if factor < 0.5:
                    weather_info = before_forecast['weather'][0]
                else:
                    weather_info = after_forecast['weather'][0]
                
                # Interpolate pop (precipitation probability)
                pop_before = before_forecast.get('pop', 0)
                pop_after = after_forecast.get('pop', 0)
                interpolated_pop = pop_before + (pop_after - pop_before) * factor
                
                # Create interpolated forecast entry
                interpolated_forecast = {
                    'dt': current_timestamp,
                    'main': {
                        'temp': interpolated_temp,
                        'feels_like': interpolated_feels
                    },
                    'weather': [weather_info],
                    'pop': interpolated_pop
                }
                hourly_forecasts.append(interpolated_forecast)
            else:
                # Use the forecast as-is
                hourly_forecasts.append(before_forecast.copy())
                hourly_forecasts[-1]['dt'] = current_timestamp
        elif before_forecast:
            # Only have before forecast, use it
            hourly_forecasts.append(before_forecast.copy())
            hourly_forecasts[-1]['dt'] = current_timestamp
        elif after_forecast:
            # Only have after forecast, use it
            hourly_forecasts.append(after_forecast.copy())
            hourly_forecasts[-1]['dt'] = current_timestamp
        
        # Move to next 2-hour interval
        current_hour += timedelta(hours=2)
    
    return hourly_forecasts


def get_weather_emoji(weather_id, description):
    """Get emoji based on weather condition"""
    # Check weather ID ranges and specific codes
    if 200 <= weather_id < 233:  # Thunderstorm
        return '⛈️'
    elif 300 <= weather_id < 322:  # Drizzle
        return '🌦️'
    elif 500 <= weather_id < 505 or 520 <= weather_id < 532:  # Rain
        return '🌧️'
    elif 600 <= weather_id < 623:  # Snow
        return '❄️'
    elif 701 <= weather_id < 782:  # Atmosphere (fog, mist, etc.)
        return '🌫️'
    elif weather_id == 800:  # Clear
        return '☀️'
    elif weather_id == 801:  # Few clouds
        return '🌤️'
    elif weather_id == 802:  # Scattered clouds
        return '⛅'
    elif weather_id == 803 or weather_id == 804:  # Broken/Overcast clouds
        return '☁️'
    
    # Fallback based on description
    desc_lower = description.lower()
    if 'clear' in desc_lower or 'sunny' in desc_lower:
        return '☀️'
    elif 'cloud' in desc_lower:
        if 'few' in desc_lower or 'scattered' in desc_lower:
            return '⛅'
        return '☁️'
    elif 'rain' in desc_lower:
        if 'drizzle' in desc_lower:
            return '🌦️'
        return '🌧️'
    elif 'storm' in desc_lower or 'thunder' in desc_lower:
        return '⛈️'
    elif 'snow' in desc_lower:
        return '❄️'
    elif 'fog' in desc_lower or 'mist' in desc_lower or 'haze' in desc_lower:
        return '🌫️'
    else:
        return '🌤️'


def generate_temperature_chart(forecast_list):
    """Generate a compact temperature chart as base64 encoded image"""
    try:
        # Filter to next 24 hours
        now = datetime.now().timestamp()
        next_24h = [f for f in forecast_list if f['dt'] <= now + 86400][:8]  # Up to 8 forecasts (24 hours)
        
        if not next_24h:
            return None
        
        times = [datetime.fromtimestamp(f['dt']).strftime("%I%p").lstrip('0') for f in next_24h]
        temps = [f['main']['temp'] for f in next_24h]
        feels_like = [f['main']['feels_like'] for f in next_24h]
        
        # Create compact figure
        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.plot(times, temps, 'o-', linewidth=2, markersize=6, color='#e74c3c', label='Temp')
        ax.plot(times, feels_like, 's--', linewidth=1.5, markersize=4, color='#3498db', alpha=0.6, label='Feels')
        ax.fill_between(times, temps, alpha=0.2, color='#e74c3c')
        ax.set_ylabel('°F', fontsize=10, fontweight='bold')
        ax.set_xlabel('Time', fontsize=10)
        ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
        ax.legend(loc='upper right', framealpha=0.9, fontsize=9)
        ax.set_facecolor('#fafafa')
        fig.patch.set_facecolor('white')
        plt.tight_layout(pad=1.0)
        
        # Convert to base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=80, bbox_inches='tight', facecolor='white', edgecolor='none')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close(fig)
        
        return img_base64
    except Exception as e:
        print(f"Error generating temperature chart: {e}")
        return None




def format_weather_email(current_data, forecast_data, recipient_name=None, news_articles=None, historical_fact=None, stock_data=None, movie_recommendation=None, xkcd_comic=None):
    """Format weather data and news into a compact, focused email"""
    if not current_data or not forecast_data:
        return "Error: Could not fetch weather data."
    
    # Current weather data
    current_temp = round(current_data['main']['temp'])
    feels_like = round(current_data['main']['feels_like'])
    description = current_data['weather'][0]['description'].title()
    city_name = current_data['name']
    weather_id = current_data['weather'][0]['id']
    weather_emoji = get_weather_emoji(weather_id, description)
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Get sunrise/sunset times
    sunrise_timestamp = current_data['sys']['sunrise']
    sunset_timestamp = current_data['sys']['sunset']
    sunrise_time = datetime.fromtimestamp(sunrise_timestamp).strftime("%I:%M %p").lstrip('0')
    sunset_time = datetime.fromtimestamp(sunset_timestamp).strftime("%I:%M %p").lstrip('0')
    
    # Get forecast from 8am to 10pm (every 2 hours)
    now = datetime.now()
    
    # If before 8am, show today's forecast
    # If 8am or later, show tomorrow's forecast (since script sends at 8am for the day ahead)
    if now.hour < 10:
        target_date = now
    else:
        target_date = now + timedelta(days=1)
    
    start_time = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = target_date.replace(hour=22, minute=0, second=0, microsecond=0)  # 10pm
    
    start_timestamp = start_time.timestamp()
    end_timestamp = end_time.timestamp()
    
    forecast_list = forecast_data['list']
    
    # Filter forecasts to 8am-midnight range and create hourly entries
    filtered_forecasts = [f for f in forecast_list if start_timestamp <= f['dt'] <= end_timestamp]
    
    # If we have hourly data (from One Call API), use it directly
    # Otherwise, interpolate from 3-hourly data
    if len(filtered_forecasts) > 0:
        # Check if data is hourly (intervals < 2 hours) or 3-hourly
        if len(filtered_forecasts) > 1:
            time_diff = filtered_forecasts[1]['dt'] - filtered_forecasts[0]['dt']
            is_hourly = time_diff < 7200  # Less than 2 hours = hourly
            
            if is_hourly:
                # Already hourly data, use it
                next_24h_forecasts = filtered_forecasts
            else:
                # 3-hourly data, interpolate to create hourly entries
                next_24h_forecasts = interpolate_to_hourly(filtered_forecasts, start_time, end_time)
        else:
            next_24h_forecasts = filtered_forecasts
    else:
        next_24h_forecasts = []
    
    # Get moon phase
    moon_phase_name, moon_phase_emoji = get_moon_phase()
    
    # Calculate high/low from forecast
    if next_24h_forecasts:
        temps = [round(f['main']['temp']) for f in next_24h_forecasts]
        high_temp = max(temps) if temps else current_temp
        low_temp = min(temps) if temps else current_temp
    else:
        high_temp = current_temp
        low_temp = current_temp
    
    # Create preview text for email inbox
    preview_text = f"In {city_name}, the high is {high_temp}° and the low is {low_temp}°. You can expect {description.lower()} today. Open up to see some of the top news stories of the day."
    
    # Personalize greeting
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi,"
    
    # Build compact, focused email
    email_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f5f5f5;">
        <!-- Preview Text (hidden in email, shows in inbox preview) -->
        <div style="display: none; max-height: 0; overflow: hidden; mso-hide: all;">{preview_text}</div>
        <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; padding: 20px;">
            <!-- Current Weather - Three Column Layout -->
            <div style="padding: 15px 0; border-bottom: 2px solid #e0e0e0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <!-- Column 1: Location & Date -->
                        <td style="width: 33%; vertical-align: top;">
                            <div style="font-size: 14px; font-weight: 500; color: #333; line-height: 1.4;">{city_name}</div>
                            <div style="font-size: 12px; color: #999; margin-top: 2px;">{current_date}</div>
                        </td>
                        
                        <!-- Column 2: Current Weather -->
                        <td style="width: 34%; vertical-align: top;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="vertical-align: middle; text-align: right; padding-right: 8px; width: 50%;">
                                        <div style="font-size: 14px; font-weight: 500; color: #333; line-height: 1.4;">{current_temp}°F</div>
                                        <div style="font-size: 12px; color: #666; margin-top: 2px;">{description}</div>
                                    </td>
                                    <td style="font-size: 32px; vertical-align: middle; text-align: left; padding-left: 8px; width: 50%;">{weather_emoji}</td>
                                </tr>
                            </table>
                        </td>
                        
                        <!-- Column 3: Moon Phase -->
                        <td style="width: 33%; text-align: right; vertical-align: top;">
                            <table style="margin-left: auto; border-collapse: collapse;">
                                <tr>
                                    <td style="vertical-align: middle; text-align: right; padding-right: 12px;">
                                        <div style="font-size: 14px; font-weight: 500; color: #333; line-height: 1.4;">{moon_phase_name}</div>
                                        <div style="font-size: 12px; color: #666; margin-top: 2px;">Moon Phase</div>
                                    </td>
                                    <td style="font-size: 32px; vertical-align: middle;">{moon_phase_emoji}</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
                <!-- Sunrise/Sunset -->
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #f0f0f0;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="text-align: left; font-size: 14px; color: #666;">🌅 {sunrise_time}</td>
                            <td style="text-align: right; font-size: 14px; color: #666;">🌇 {sunset_time}</td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <!-- Hourly Forecast -->
            <div style="padding-top: 15px;">
                <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #333; font-weight: bold;">Today's Forecast</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 2px solid #e0e0e0;">
                            <th style="padding: 8px 5px; text-align: left; font-size: 12px; color: #666; font-weight: 600;">Time</th>
                            <th style="padding: 8px 5px; text-align: center; font-size: 12px; color: #666; font-weight: 600;">Condition</th>
                            <th style="padding: 8px 5px; text-align: right; font-size: 12px; color: #666; font-weight: 600;">Temp</th>
                            <th style="padding: 8px 5px; text-align: left; font-size: 12px; color: #666; font-weight: 600;">Description</th>
                            <th style="padding: 8px 5px; text-align: center; font-size: 12px; color: #666; font-weight: 600;">Rain</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Add hourly forecast entries with rain probability
    for i, forecast in enumerate(next_24h_forecasts):
        forecast_time = datetime.fromtimestamp(forecast['dt'])
        time_str = forecast_time.strftime("%I %p").lstrip('0')  # Show only hour, no minutes
        forecast_temp = round(forecast['main']['temp'])
        forecast_desc = forecast['weather'][0]['description'].title()
        forecast_weather_id = forecast['weather'][0]['id']
        forecast_emoji = get_weather_emoji(forecast_weather_id, forecast_desc)
        
        # Get precipitation probability (pop) - OpenWeatherMap provides this as a decimal (0-1)
        pop = forecast.get('pop', 0) * 100  # Convert to percentage
        pop_display = f"{int(pop)}%" if pop > 0 else "—"
        pop_color = "#3498db" if pop > 50 else "#7f8c8d" if pop > 0 else "#999"
        
        # Alternate row background for readability
        row_bg = "#fafafa" if i % 2 == 0 else "#ffffff"
        
        email_body += f"""
                        <tr style="background-color: {row_bg}; border-bottom: 1px solid #f0f0f0;">
                            <td style="padding: 10px 5px; font-size: 13px; color: #333; font-weight: 500;">{time_str}</td>
                            <td style="padding: 10px 5px; text-align: center; font-size: 24px;">{forecast_emoji}</td>
                            <td style="padding: 10px 5px; text-align: right; font-size: 15px; font-weight: bold; color: #333;">{forecast_temp}°F</td>
                            <td style="padding: 10px 5px; font-size: 12px; color: #666;">{forecast_desc}</td>
                            <td style="padding: 10px 5px; text-align: center; font-size: 12px; font-weight: 500; color: {pop_color};">{pop_display}</td>
                        </tr>
        """
    
    email_body += f"""
                    </tbody>
                </table>
            </div>
    """
    
    # Add News Section if articles are available
    if news_articles and len(news_articles) > 0:
        email_body += """
            <!-- News Section -->
            <div style="padding-top: 20px; border-top: 2px solid #e0e0e0; margin-top: 20px;">
                <h3 style="margin: 0 0 10px 0; font-size: 16px; color: #333; font-weight: bold;">📰 Top News</h3>
        """
        
        # Add S&P 500 data if available
        if stock_data:
            change = stock_data['change']
            percent_change = stock_data['percent_change']
            is_positive = stock_data['is_positive']
            arrow = "▲" if is_positive else "▼"
            color = "#27ae60" if is_positive else "#e74c3c"
            sign = "+" if is_positive else ""
            
            email_body += f"""
                <div style="background-color: #f8f9fa; padding: 10px 15px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid {color};">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="font-size: 13px; color: #666; font-weight: 500;">S&P 500</td>
                            <td style="text-align: right; font-size: 15px; font-weight: 600; color: {color};">{arrow} {sign}{percent_change}%</td>
                        </tr>
                    </table>
                </div>
            """
        
        for i, article in enumerate(news_articles):
            title = article.get('title', 'No title')
            description = article.get('description', '')
            url = article.get('url', '#')
            source = article.get('source', {}).get('name', 'Unknown')
            
            # Truncate description if too long
            if description and len(description) > 200:
                description = description[:200] + '...'
            
            # Only show description if available
            desc_html = f'<div style="font-size: 12px; color: #666; line-height: 1.5; margin-top: 5px;">{description}</div>' if description else ''
            
            email_body += f"""
                <div style="padding: 12px 0; border-bottom: 1px solid #f0f0f0;">
                    <div style="font-size: 14px; font-weight: 600; color: #333; line-height: 1.4; margin-bottom: 5px;">
                        <a href="{url}" style="color: #2c3e50; text-decoration: none;">{title}</a>
                    </div>
                    {desc_html}
                    <div style="margin-top: 6px;">
                        <a href="{url}" style="font-size: 11px; color: #3498db; text-decoration: none; font-weight: 500;">Read more →</a>
                        <span style="font-size: 11px; color: #999; margin-left: 8px;">• {source}</span>
                    </div>
                </div>
            """
        
        email_body += """
            </div>
        """
    
    # Add Historical Fact Section if available
    if historical_fact:
        year = historical_fact.get('year', '')
        text = historical_fact.get('text', '')
        url = historical_fact.get('url', '')
        
        email_body += f"""
            <!-- Historical Fact Section -->
            <div style="padding: 20px 0; border-top: 2px solid #e0e0e0; margin-top: 20px;">
                <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #333; font-weight: bold;">📜 On This Day in History</h3>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #9b59b6;">
                    <div style="font-size: 18px; font-weight: 600; color: #8e44ad; margin-bottom: 8px;">{year}</div>
                    <div style="font-size: 13px; color: #555; line-height: 1.6;">{text}</div>
                    {f'<div style="margin-top: 10px;"><a href="{url}" style="font-size: 11px; color: #3498db; text-decoration: none; font-weight: 500;">Learn more →</a></div>' if url else ''}
                </div>
            </div>
        """
    
    # Add Movie Recommendation Section if available
    if movie_recommendation:
        title = movie_recommendation.get('title', '')
        overview = movie_recommendation.get('overview', '')
        poster_url = movie_recommendation.get('poster_url', '')
        release_date = movie_recommendation.get('release_date', 'N/A')
        rating = movie_recommendation.get('rating', 0)
        genres = movie_recommendation.get('genres', 'N/A')
        runtime = movie_recommendation.get('runtime', 'N/A')
        tmdb_url = movie_recommendation.get('tmdb_url', '')
        
        # Format release year
        release_year = release_date.split('-')[0] if release_date and release_date != 'N/A' else 'N/A'
        
        # Create star rating visualization
        full_stars = int(rating / 2)  # Convert 10-point scale to 5-star
        half_star = 1 if (rating / 2) - full_stars >= 0.5 else 0
        empty_stars = 5 - full_stars - half_star
        stars = '⭐' * full_stars + ('✨' if half_star else '') + '☆' * empty_stars
        
        # Truncate overview if too long
        if len(overview) > 300:
            overview = overview[:297] + '...'
        
        email_body += f"""
            <!-- Movie Recommendation Section -->
            <div style="padding: 20px 0; border-top: 2px solid #e0e0e0; margin-top: 20px;">
                <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #333; font-weight: bold;">🎬 Movie Recommendation of the Day</h3>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #e74c3c;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            {'<td style="width: 100px; vertical-align: top; padding-right: 15px;"><a href="' + tmdb_url + '"><img src="' + poster_url + '" alt="' + title + ' poster" style="width: 100px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);" /></a></td>' if poster_url else ''}
                            <td style="vertical-align: top;">
                                <div style="font-size: 16px; font-weight: 600; color: #c0392b; margin-bottom: 6px;">
                                    <a href="{tmdb_url}" style="color: #c0392b; text-decoration: none;">{title}</a>
                                    <span style="font-size: 13px; color: #999; font-weight: normal;"> ({release_year})</span>
                                </div>
                                <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
                                    <span style="margin-right: 10px;">{stars} {rating}/10</span>
                                    <span style="margin-right: 10px;">• {genres}</span>
                                    <span>• {runtime}</span>
                                </div>
                                <div style="font-size: 13px; color: #555; line-height: 1.5; margin-bottom: 10px;">{overview}</div>
                                <div>
                                    <a href="{tmdb_url}" style="font-size: 11px; color: #3498db; text-decoration: none; font-weight: 500;">View on TMDB →</a>
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>
            </div>
        """
    
    # Add XKCD Comic if available
    if xkcd_comic:
        title = xkcd_comic.get('title', '')
        img_url = xkcd_comic.get('img', '')
        alt_text = xkcd_comic.get('alt', '')
        link = xkcd_comic.get('link', '')
        label = xkcd_comic.get('label', 'Comic of the Day')
        is_new = xkcd_comic.get('is_new', False)
        
        email_body += f"""
            <!-- XKCD Comic -->
            <div style="padding-top: 20px; border-top: 2px solid #e0e0e0; margin-top: 20px;">
                <h3 style="margin: 0 0 8px 0; font-size: 16px; color: #333; font-weight: bold;">💥 XKCD Comic</h3>
                <div style="margin: 0 0 12px 0; font-size: 13px; color: #666;">{label}</div>
                <div style="text-align: center; background-color: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <a href="{link}" style="text-decoration: none;">
                        <img src="{img_url}" alt="{alt_text}" style="max-width: 100%; height: auto; border-radius: 4px;" />
                    </a>
                    <div style="margin-top: 12px; font-size: 14px; font-weight: 600; color: #333;">{title}</div>
                    <div style="margin-top: 6px; font-size: 11px; color: #666; font-style: italic; line-height: 1.4;">"{alt_text}"</div>
                    <div style="margin-top: 8px;">
                        <a href="{link}" style="font-size: 11px; color: #3498db; text-decoration: none; font-weight: 500;">View on xkcd.com →</a>
                    </div>
                </div>
            </div>
        """
    
    email_body += f"""
            <!-- Footer -->
            <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #e0e0e0; text-align: center; font-size: 11px; color: #999;">
                {greeting} Weather from OpenWeatherMap{', News from NewsAPI' if news_articles else ''}{', History from Wikipedia' if historical_fact else ''}{', Movies from TMDB' if movie_recommendation else ''}{', Comic from XKCD' if xkcd_comic else ''}
            </div>
        </div>
    </body>
    </html>
    """
    
    return email_body


def send_email(body, recipient_email, recipient_name=None):
    """Send email with weather information"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🛸 Daily Brief - {datetime.now().strftime('%m/%d/%Y')}"
        msg['From'] = f"Scout <{EMAIL_ADDRESS}>"
        msg['To'] = recipient_email
        
        # Create HTML part
        html_part = MIMEText(body, 'html')
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        
        name_str = f" to {recipient_name}" if recipient_name else ""
        print(f"Email sent successfully{name_str} ({recipient_email}) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {e}")
        return False


def load_user_list():
    """Load user list from CSV file"""
    users = []
    try:
        with open(EMAIL_LIST_CSV, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                users.append({
                    'name': row.get('Name', '').strip(),
                    'email': row.get('Email', '').strip(),
                    'city': row.get('City', '').strip(),
                    'state': row.get('State', '').strip(),
                    'zip': row.get('Zip', '').strip()
                })
        print(f"Loaded {len(users)} user(s) from {EMAIL_LIST_CSV}")
        return users
    except FileNotFoundError:
        print(f"Error: {EMAIL_LIST_CSV} not found.")
        return []
    except Exception as e:
        print(f"Error reading {EMAIL_LIST_CSV}: {e}")
        return []


def send_weather_email_to_user(user, news_articles=None, historical_fact=None, stock_data=None, movie_recommendation=None, xkcd_comic=None):
    """Fetch weather and send email to a single user"""
    name = user['name']
    email = user['email']
    city = user['city']
    state = user['state']
    zip_code = user['zip']
    
    if not email:
        print(f"Skipping user {name}: No email address")
        return False
    
    if not city:
        print(f"Skipping user {name}: No city specified")
        return False
    
    print(f"Processing weather for {name} ({email}) in {city}, {state if state else 'N/A'}")
    
    # Get weather data
    current_data, forecast_data = get_weather_data(city, state, zip_code)
    
    if current_data and forecast_data:
        # Format email with all content
        email_body = format_weather_email(current_data, forecast_data, name, news_articles, historical_fact, stock_data, movie_recommendation, xkcd_comic)
        
        # Send email
        return send_email(email_body, email, name)
    else:
        print(f"Failed to fetch weather data for {city}. Email not sent to {email}.")
        return False


def send_daily_weather_email():
    """Main function to fetch weather and send emails to all users"""
    print(f"Running scheduled task at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load user list
    users = load_user_list()
    
    if not users:
        print("No users found. Email not sent.")
        return
    
    # Fetch news once for all users (to save API calls)
    print("Fetching top news stories...")
    news_articles = get_top_news_stories(num_stories=8)
    if news_articles:
        print(f"Found {len(news_articles)} news articles")
    else:
        print("No news articles found or NewsAPI key not configured")
    
    # Fetch historical fact once for all users
    print("Fetching historical fact...")
    historical_fact = get_historical_fact()
    if historical_fact:
        print(f"Found historical fact from {historical_fact.get('year')}")
    else:
        print("No historical fact found")
    
    # Fetch stock market data
    print("Fetching stock market data...")
    stock_data = get_stock_market_data()
    if stock_data:
        print(f"S&P 500: {stock_data['change']:+.2f} ({stock_data['percent_change']:+.2f}%)")
    else:
        print("No stock market data found")
    
    # Fetch movie recommendation
    print("Fetching movie recommendation...")
    movie_recommendation = get_movie_recommendation()
    if movie_recommendation:
        print(f"Movie recommendation: {movie_recommendation.get('title')} ({movie_recommendation.get('rating')}/10)")
    else:
        print("No movie recommendation found")
    
    # Fetch XKCD comic
    print("Fetching XKCD comic...")
    xkcd_comic = get_xkcd_comic()
    if xkcd_comic:
        status = "NEW" if xkcd_comic.get('is_new') else "RANDOM"
        print(f"Found XKCD ({status}) #{xkcd_comic.get('num')}: {xkcd_comic.get('title')}")
    else:
        print("No XKCD comic found")
    
    # Send email to each user
    success_count = 0
    for user in users:
        if send_weather_email_to_user(user, news_articles, historical_fact, stock_data, movie_recommendation, xkcd_comic):
            success_count += 1
        # Small delay between emails to avoid rate limiting
        time.sleep(1)
    
    print(f"Completed: {success_count}/{len(users)} emails sent successfully.")


def main():
    """Main function to schedule and run the email task"""
    # Validate configuration
    if not WEATHER_API_KEY:
        print("Error: WEATHER_API_KEY not set in environment variables")
        return
    
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("Error: EMAIL_ADDRESS or EMAIL_PASSWORD not set in environment variables")
        return
    
    # Check if running in "once" mode (for Task Scheduler)
    run_once = os.getenv('RUN_ONCE', 'false').lower() == 'true'
    
    if run_once:
        # Run once and exit (for Task Scheduler)
        print("Running in single-execution mode...")
        send_daily_weather_email()
    else:
        # Schedule the email to be sent every day at 8:00 AM
        schedule.every().day.at("08:00").do(send_daily_weather_email)
        
        print("Weather email scheduler started. Emails will be sent daily at 8:00 AM.")
        print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C to stop.")
        
        # Run scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()

