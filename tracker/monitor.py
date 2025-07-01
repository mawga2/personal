import csv
import time
from datetime import datetime, timezone
import urllib.request
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

# Configuration
STEAM_URLS_FILE = 'steam_urls.txt'
GAMES_DB_FILE = 'steam_games_db.csv'

def send_notification(subject, body):
    # Email configuration from environment variables
    smtp_server = 'smtp.gmail.com'
    smtp_port = '587'
    sender_email = 'send543210@gmail.com'
    sender_password = 'crre dlym rjfp fscj'
    recipient_email = 'u3606179@connect.hku.hk'

    # Validate environment variables
    if not all([sender_email, sender_password]):
        print("Error: SENDER_EMAIL or SENDER_PASSWORD not set in environment variables.")
        return False

    # Create email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to SMTP server
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Enable TLS
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print("Email sent successfully.")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def scrape(url):
    try:
        req = urllib.request.urlopen(url)
        html = req.read()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
    
    soup = BeautifulSoup(html, 'html.parser')

    title_div = soup.find('div', {'class': 'apphub_AppName'}, id='appHubAppName_responsive')
    if not title_div:
        print(f"Skipping {url}: No title found")
        return None
    title = title_div.text.strip()

    # Extract User Review
    user_review = "No reviews"
    review_spans = soup.find_all('span', {'class': 'game_review_summary'})
    if review_spans:
        user_review = review_spans[0].text.strip()

    # Extract Developer & Publisher
    developer = "No Developer"
    publisher = "No Publisher"
    devpub = soup.find_all('div', {'class': 'dev_row'})
    if devpub:
        if len(devpub) > 0:
            developer = devpub[0].find('a').text.strip() if devpub[0].find('a') else "No Developer"
        if len(devpub) > 1:
            publisher = devpub[1].find('a').text.strip() if devpub[1].find('a') else "No Publisher"

    # Extract Tags
    tags = []
    tag_list = soup.find_all('a', {'class': 'app_tag'})
    if tag_list:
        tags = [tag.text.strip() for tag in tag_list]

    # Extract Price
    price = "TBD"
    discount_pct = "N/A"

    purchase_div = soup.find('div', {'class': 'game_area_purchase_game'})
    if purchase_div:
        # Check for discounted price first
        discount_final_price = purchase_div.find('div', {'class': 'discount_final_price'})
        if discount_final_price:
            price = discount_final_price.text.strip()
            discount_pct_tag = purchase_div.find('div', {'class': 'discount_pct'})
            if discount_pct_tag:
                discount_pct = discount_pct_tag.text.strip()
        else:
            # Check for regular price
            price_div = purchase_div.find('div', {'class': 'game_purchase_price price'})
            if price_div and price_div.text.strip():
                price = price_div.text.strip()
    else:
        coming_soon = soup.find('div', {'class': 'comingsoon'})
        if coming_soon:
            price = "Coming Soon"

    return (title, developer, publisher, tags, user_review, price, discount_pct, url)

def scrape_all(urls):
    results = []
    for url in urls:
        result = scrape(url)
        if result:
            results.append(result)
    return results

def load_previous_data():
    """Load previously scraped game data from the database file."""
    try:
        with open(GAMES_DB_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = {row['url']: row for row in reader}
            return data
    except FileNotFoundError:
        return {}

def save_current_data(games_data):
    """Save current game data directly to the CSV file."""
    try:
        with open(GAMES_DB_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'title', 'developer', 'publisher', 'tags', 
                'user_review', 'price', 'discount_pct', 'url'
            ])
            writer.writeheader()
            writer.writerows(games_data.values())
        print("Successfully updated CSV file")
        return True
    except Exception as e:
        print(f"ERROR: Failed to save CSV file: {e}")
        return False

def check_for_changes(old_data, new_data):
    """Compare old and new data to detect changes worth notifying."""
    notifications = []
    
    for url, new_game in new_data.items():
        if url not in old_data:
            notifications.append(
                f"New game being tracked: {new_game['title']}\n"
                f"Price: {new_game['price']}\n"
                f"URL: {url}"
            )
            continue
            
        old_game = old_data[url]
        
        if old_game['price'] != new_game['price']:
            notifications.append(
                f"Price change for {new_game['title']}:\n"
                f"Old price: {old_game['price']}\n"
                f"New price: {new_game['price']}\n"
                f"Discount: {new_game['discount_pct']}\n"
                f"URL: {url}"
            )
        
        if old_game['price'] == "Coming Soon" and new_game['price'] != "Coming Soon":
            notifications.append(
                f"Game released: {new_game['title']}\n"
                f"Now available for: {new_game['price']}\n"
                f"URL: {url}"
            )
        
        if old_game['discount_pct'] == "N/A" and new_game['discount_pct'] != "N/A":
            notifications.append(
                f"New discount for {new_game['title']}:\n"
                f"Discount: {new_game['discount_pct']}\n"
                f"New price: {new_game['price']}\n"
                f"URL: {url}"
            )
    
    return notifications

def prepare_notification_content(notifications):
    """Prepare the email content from notifications."""
    if not notifications:
        return None
        
    subject = f"Steam Updates - {len(notifications)} changes detected"
    body = "\n\n".join(notifications)
    return subject, body

def run_monitoring_cycle():
    """Run one complete monitoring cycle."""
    old_data = load_previous_data()
    
    with open(STEAM_URLS_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    scraped_data = scrape_all(urls)
    
    new_data = {}
    for item in scraped_data:
        title, developer, publisher, tags, user_review, price, discount_pct, url = item
        new_data[url] = {
            'title': title,
            'developer': developer,
            'publisher': publisher,
            'tags': ', '.join(tags),
            'user_review': user_review,
            'price': price,
            'discount_pct': discount_pct,
            'url': url
        }
    
    notifications = check_for_changes(old_data, new_data)
    notification_content = prepare_notification_content(notifications)
    
    if not save_current_data(new_data):
        print("Failed to save CSV data")
        return None
    
    return notification_content

def is_scan_time():
    """Check if current UTC time is 0000, 0800, or 1600."""
    now = datetime.now(timezone.utc)
    return now.hour in [0, 8, 16] and now.minute == 0

def main():
    notification_content = run_monitoring_cycle()
    if notification_content:
        subject, body = notification_content
        if send_notification(subject, body):
            print("Notification sent successfully.")
            return 0
        else:
            print("Failed to send notification.")
            return 1
    else:
        print("No changes detected in this cycle.")
        return 0

if __name__ == "__main__":
    sys.exit(main())