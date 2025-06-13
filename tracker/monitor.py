# game_monitor.py
import time
import schedule
import subprocess
import csv
from datetime import datetime
import os
import win32com.client

class GameMonitor:
    def __init__(self):
        self.previous_data = {}
        self.current_data = {}
        self.csv_file = 'steam_games.csv'
        self.previous_csv = 'previous_steam_games.csv'
        
    def run_scraper(self):
        """Run the steam scraper and process the results"""
        print(f"{datetime.now()} - Running steam scraper...")
        try:
            # Run the scraper as a subprocess
            subprocess.run(['python', 'steam_scraper.py'], check=True)
            
            # Load and compare data
            self.load_current_data()
            changes = self.detect_changes()
            
            if changes:
                self.send_notification(changes)
                # Update previous data file
                os.replace(self.csv_file, self.previous_csv)
            else:
                print(f"{datetime.now()} - No changes detected.")
                
        except Exception as e:
            print(f"Error running scraper: {e}")
    
    def load_current_data(self):
        """Load the current scraped data from CSV"""
        self.current_data = {}
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.current_data[row['url']] = row
    
    def detect_changes(self):
        """Detect changes between current and previous data"""
        changes = []
        
        # Load previous data if exists
        if os.path.exists(self.previous_csv):
            with open(self.previous_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.previous_data = {row['url']: row for row in reader}
        else:
            # First run, no previous data
            print("No previous data found. This appears to be the first run.")
            return changes
        
        # Check for new games
        new_games = set(self.current_data.keys()) - set(self.previous_data.keys())
        for url in new_games:
            game = self.current_data[url]
            changes.append({
                'type': 'new',
                'title': game['title'],
                'price': game['price'],
                'discount': game['discount_pct'],
                'url': url
            })
        
        # Check for price changes and discounts
        for url, current_game in self.current_data.items():
            if url in self.previous_data:
                previous_game = self.previous_data[url]
                
                # Price change detection
                if current_game['price'] != previous_game['price']:
                    changes.append({
                        'type': 'price_change',
                        'title': current_game['title'],
                        'old_price': previous_game['price'],
                        'new_price': current_game['price'],
                        'url': url
                    })
                
                # Discount detection
                if (current_game['discount_pct'] != previous_game['discount_pct'] and 
                    current_game['discount_pct'] != 'N/A'):
                    changes.append({
                        'type': 'discount',
                        'title': current_game['title'],
                        'discount': current_game['discount_pct'],
                        'price': current_game['price'],
                        'url': url
                    })
        
        return changes
    
    def send_notification(self, changes):
        """Send email notification about changes"""
        print(f"{datetime.now()} - Sending notification about {len(changes)} changes...")
        
        # Prepare email body
        body_lines = ["Game updates detected:"]
        
        for change in changes:
            if change['type'] == 'new':
                body_lines.append(
                    f"🆕 NEW: {change['title']} - Price: {change['price']} "
                    f"(Discount: {change['discount']}) - {change['url']}"
                )
            elif change['type'] == 'price_change':
                body_lines.append(
                    f"💰 PRICE CHANGE: {change['title']} - "
                    f"From {change['old_price']} to {change['new_price']} - {change['url']}"
                )
            elif change['type'] == 'discount':
                body_lines.append(
                    f"🎉 DISCOUNT: {change['title']} - "
                    f"{change['discount']} off! Now {change['price']} - {change['url']}"
                )
        
        body = "\n".join(body_lines)
        
        # Send email
        try:
            ol = win32com.client.Dispatch("outlook.application")
            olmailitem = 0x0
            newmail = ol.CreateItem(olmailitem)
            newmail.Subject = 'Steam Game Updates Detected'
            newmail.To = 'u3606179@connect.hku.hk'
            newmail.Body = body
            newmail.Send()
            print("Notification email sent successfully.")
        except Exception as e:
            print(f"Failed to send notification email: {e}")
    
    def start(self):
        """Start the monitoring service"""
        print("Starting Steam Game Monitor...")
        print(f"First check will run immediately, then every 8 hours.")
        
        # Run immediately
        self.run_scraper()
        
        # Schedule every 8 hours
        schedule.every(8).hours.do(self.run_scraper)
        
        # Keep the program running
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    monitor = GameMonitor()
    monitor.start()