import csv
import time
from datetime import datetime, timezone
from send_noti import send_notification
from steam_scraper import scrape_all

# Configuration
STEAM_URLS_FILE = 'steam_urls.txt'
GAMES_DB_FILE = 'steam_games_db.csv'

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
    """Main function with scheduled monitoring."""
    print("Starting Steam monitoring service...")
    
    while True:
        if is_scan_time():
            print(f"Running scan at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
            notification_content = run_monitoring_cycle()
            
            if notification_content:
                subject, body = notification_content
                if send_notification(subject, body):
                    print("Notification sent successfully.")
                else:
                    print("Failed to send notification.")
            else:
                print("No changes detected in this cycle.")
            
            time.sleep(61)
        else:
            time.sleep(60)

if __name__ == "__main__":
    main()