import csv
import os
from send_noti import send_notification
from steam_scraper import scrape_all

# Configuration
STEAM_URLS_FILE = os.path.join(os.path.dirname(__file__), 'steam_urls.txt')
GAMES_DB_FILE = os.path.join(os.path.dirname(__file__), 'steam_games_db.csv')
TEMP_CSV_FILE = os.path.join(os.path.dirname(__file__), 'temp_steam_games.csv')

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
    """Save current game data to the temporary CSV file."""
    os.makedirs(os.path.dirname(TEMP_CSV_FILE), exist_ok=True)
    
    with open(TEMP_CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'title', 'developer', 'publisher', 'tags', 
            'user_review', 'price', 'discount_pct', 'url'
        ])
        writer.writeheader()
        writer.writerows(games_data.values())
    
    if os.path.exists(TEMP_CSV_FILE):
        print("Successfully saved temporary CSV file")
    else:
        print("ERROR: Failed to save temporary CSV file!")
        return False
    
    # Compare temporary CSV with existing database file
    update_needed = True
    if os.path.exists(GAMES_DB_FILE):
        try:
            with open(GAMES_DB_FILE, 'r', encoding='utf-8') as old_f, open(TEMP_CSV_FILE, 'r', encoding='utf-8') as new_f:
                if old_f.read() == new_f.read():
                    print("No changes in CSV content. Skipping update.")
                    update_needed = False
        except Exception as e:
            print(f"Error comparing CSV files: {e}")
    
    # Update the database file if needed
    if update_needed:
        try:
            os.replace(TEMP_CSV_FILE, GAMES_DB_FILE)
            print("Successfully updated database CSV file")
        except Exception as e:
            print(f"ERROR: Failed to update database CSV file: {e}")
            return False
    else:
        os.remove(TEMP_CSV_FILE)
    
    return True

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

def main():
    """Main function to be called by the GitHub workflow."""
    print("=== Starting monitoring cycle ===")
    notification_content = run_monitoring_cycle()
    
    if notification_content:
        subject, body = notification_content
        if send_notification(subject, body):
            print("Notification sent successfully.")
        else:
            print("Failed to send notification.")
            exit(1) 
    else:
        print("No changes detected in this cycle.")

if __name__ == "__main__":
    main()