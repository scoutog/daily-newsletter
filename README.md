# 📧 Daily Brief - Automated Email Service

A Python-based automated email service that sends personalized daily briefings with weather forecasts, top news stories, historical facts, stock market updates, movie recommendations, and a daily comic to your recipients.

## ✨ Features

- **🌤️ Detailed Weather Forecasts**: Current conditions, hourly forecasts (8am-10pm), sunrise/sunset times, and moon phases
- **📰 Top News Stories**: Latest headlines from the past 24 hours (powered by NewsAPI)
- **📈 Stock Market Data**: S&P 500 index performance
- **📜 Historical Facts**: Learn what happened on this day in history (via Wikipedia)
- **🎬 Movie Recommendations**: Daily curated movie suggestion from top-rated films (powered by TMDB)
- **💥 Daily Comic**: Latest XKCD comic for a smile
- **👥 Multi-Recipient Support**: Send personalized emails to multiple people with location-specific weather
- **🎨 Beautiful HTML Emails**: Clean, responsive email design optimized for all devices

## 📋 Requirements

- Python 3.8 or higher
- Valid API keys (see Setup section)
- Gmail account with App Password (or other SMTP server)

## 🚀 Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get API Keys

You'll need to obtain free API keys from:

- **OpenWeatherMap** (required): [https://openweathermap.org/api](https://openweathermap.org/api)
- **NewsAPI** (optional): [https://newsapi.org/](https://newsapi.org/)
- **TMDB** (optional): [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)

### 3. Configure Environment Variables

1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and fill in your credentials:
   ```env
   WEATHER_API_KEY=your_openweathermap_api_key_here
   NEWS_API_KEY=your_newsapi_key_here
   TMDB_API_KEY=your_tmdb_api_key_here
   EMAIL_ADDRESS=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password_here
   ```

#### Gmail App Password Setup

For Gmail, you need to create an App Password:
1. Enable 2-factor authentication on your Google account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Use this password in your `.env` file

### 4. Configure Recipients

1. Copy `email-list.example.csv` to `email-list.csv`:
   ```bash
   cp email-list.example.csv email-list.csv
   ```

2. Edit `email-list.csv` to add your recipients:
   ```csv
   Name,Email,City,State,Zip
   John Doe,john@example.com,New York,New York,10001
   Jane Smith,jane@example.com,Los Angeles,California,90001
   ```

**Fields:**
- `Name`: Recipient's first name (used for personalization)
- `Email`: Recipient's email address
- `City`: City name for weather data
- `State`: Full state name or 2-letter code (optional)
- `Zip`: ZIP code for more accurate weather (optional)

## 📖 Usage

### Run Once

To send emails immediately:

```bash
python main.py
```

Set `RUN_ONCE=true` in your `.env` file or environment to run once and exit:

```bash
# Windows
set RUN_ONCE=true && python main.py

# Linux/Mac
RUN_ONCE=true python main.py
```

### Schedule Daily Emails

#### Option 1: Built-in Scheduler

The script includes a built-in scheduler. Simply run:

```bash
python main.py
```

By default, emails are sent daily at 8:00 AM. The script will continue running until you stop it (Ctrl+C).

#### Option 2: Windows Task Scheduler

Use the included `run_once.bat` file with Windows Task Scheduler:

1. Open Windows Task Scheduler
2. Create a new task:
   - **Trigger**: Daily at 8:00 AM
   - **Action**: Start a program
   - **Program**: Full path to `run_once.bat`
3. Configure additional settings as needed

#### Option 3: Linux/Mac Cron

Add to your crontab:

```bash
# Run daily at 8:00 AM
0 8 * * * cd /path/to/automated-email && /usr/bin/python3 main.py
```

Make sure to set `RUN_ONCE=true` in your `.env` file when using cron.

## 🛠️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WEATHER_API_KEY` | Yes | - | OpenWeatherMap API key |
| `NEWS_API_KEY` | No | - | NewsAPI key (optional, for news section) |
| `TMDB_API_KEY` | No | - | TMDB API key (optional, for movie recommendations) |
| `EMAIL_ADDRESS` | Yes | - | Sender email address |
| `EMAIL_PASSWORD` | Yes | - | Email app password |
| `SMTP_SERVER` | No | `smtp.gmail.com` | SMTP server address |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `COUNTRY_CODE` | No | `US` | Country code for weather |
| `EMAIL_LIST_CSV` | No | `email-list.csv` | Path to recipient list CSV |
| `RUN_ONCE` | No | `false` | Run once and exit (for schedulers) |

### Weather Data

The service uses OpenWeatherMap's free tier, which provides:
- Current weather conditions
- 5-day/3-hour forecasts (interpolated to show hourly data)
- Sunrise and sunset times
- Weather icons and descriptions

### News Data

News stories are fetched from NewsAPI's free tier:
- Top headlines from the past 24 hours
- US-focused news (configurable via `COUNTRY_CODE`)
- Displays up to 8 articles per email

### Movie Recommendations

Movie suggestions are fetched from The Movie Database (TMDB):
- Randomly selected from top-rated movies for quality recommendations
- Includes poster, rating, genres, runtime, and synopsis
- Pool of ~200 highly-rated films spanning different eras

## 📧 Email Contents

Each daily brief includes:

1. **Current Weather**: Temperature, conditions, and weather emoji
2. **Moon Phase**: Current lunar phase with emoji
3. **Sunrise/Sunset**: Daily sun times
4. **Hourly Forecast**: Temperature, conditions, and precipitation probability from 8am to 10pm
5. **Top News**: Latest headlines with descriptions and links
6. **S&P 500**: Market performance indicator
7. **Historical Fact**: Interesting events that happened on this day
8. **Movie Recommendation**: Curated film suggestion with poster, rating, and details
9. **XKCD Comic**: Latest webcomic for entertainment

## 🐛 Troubleshooting

### No emails being sent

- Verify your email credentials in `.env`
- Check that Gmail App Password is correctly configured
- Ensure `email-list.csv` has valid recipients
- Check firewall settings for SMTP (port 587)

### Weather data not loading

- Verify `WEATHER_API_KEY` is valid
- Check that city names in `email-list.csv` are spelled correctly
- Try using ZIP codes for more accurate location data

### News section missing

- This is optional - add `NEWS_API_KEY` to enable it
- Check NewsAPI rate limits (free tier: 100 requests/day)

### Movie recommendation missing

- This is optional - add `TMDB_API_KEY` to enable it
- Verify your TMDB API key is valid and active

### Script stops unexpectedly

- Check console output for error messages
- Verify all dependencies are installed
- Ensure Python 3.8+ is being used

## 📝 Notes

- **API Rate Limits**: Be mindful of free tier limits:
  - OpenWeatherMap: 1,000 calls/day
  - NewsAPI: 100 requests/day
  - TMDB: 1,000 requests/day
- **Email Rate Limits**: Gmail has sending limits (500/day for regular accounts)
- **Privacy**: Keep your `.env` and `email-list.csv` secure and never commit them to version control (already protected by `.gitignore`)
- **Customization**: The email HTML can be customized in the `format_weather_email()` function

## 🔒 Git Safety

The following files contain sensitive information and are already excluded via `.gitignore`:
- `.env` - Contains API keys and email passwords
- `email-list.csv` - Contains real email addresses

Safe to commit:
- `env.example` - Template with no real credentials
- `email-list.example.csv` - Template with fake emails
- `main.py` - Source code
- `README.md` - Documentation
- `requirements.txt` - Dependencies
- `run_once.bat` - Batch script
- `.gitignore` - Git ignore rules

## 🤝 Contributing

Feel free to fork this project and customize it for your needs. Some ideas:
- Add support for different email providers
- Include additional data sources (crypto prices, sports scores, etc.)
- Create different email templates
- Add weather alerts and notifications

## 📄 License

This project is provided as-is for personal use. API providers have their own terms of service.

## 🙏 Credits

- Weather data: [OpenWeatherMap](https://openweathermap.org/)
- News data: [NewsAPI](https://newsapi.org/)
- Historical facts: [Wikipedia](https://www.wikipedia.org/)
- Stock data: [Yahoo Finance](https://finance.yahoo.com/)
- Movie data: [The Movie Database (TMDB)](https://www.themoviedb.org/)
- Comics: [XKCD](https://xkcd.com/)

---

Made with ❤️ for staying informed every morning!

