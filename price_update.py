import requests
from bs4 import BeautifulSoup
import sqlite3
import smtplib
from email.message import EmailMessage
from apscheduler.schedulers.background import BackgroundScheduler
import json
import datetime

CONFIG = {
    'steam': {
        'db_url': "https://steamdb.info/app/{app_id}/",
        'new_releases_url': "https://store.steampowered.com/search/?sort_by=Released_DESC&os=win",
        'upcoming_url': "https://store.steampowered.com/search/?sort_by=Released_DESC&os=win&filter=comingsoon",
        'app_details_url': "https://store.steampowered.com/api/appdetails?appids={app_id}"
    },
    'games_to_track': {
        # Format: app_id: {'name': 'Game Name', 'track': 'release'/'discount', 'threshold': X}
        '3240220': {'name': 'GTA 5', 'track': 'discount', 'threshold': 233},
        '2927200': {'name': 'Bannerlord 2 - War Sails DLC', 'track': 'release'}
    },
    'track_new_games': True,
    'track_upcoming_releases': True,
    'check_interval_hours': 6,
    'notification': {
        'email': {
            'enabled': True,
            'sender': 'send543210@gmail.com',
            'password': 'weqxik-misgu9-rYbmob',
            'receiver': 'u3606179@connect.hku.hk'
        },
        'discord': {
            'enabled': True,
            'webhook_url': 'https://discord.com/api/webhooks/1382611510517563392/t92kBkkUlw3i-zIdg3rMsNU5HV70TPgXay34SJazOrfeGJu34OJOzaZl96Pu32q60lXh',
            'price_drop_color': 0x00ff00,  # Green
            'new_release_color': 0x7289da,  # Blurple
            'dlc_release_color': 0x9932cc   # Dark orchid
        }
    }
}

def init_db():
    """Initialize the database with tables for both price history and releases"""
    conn = sqlite3.connect('steam_tracker.db')
    c = conn.cursor()
    
    # Price history table
    c.execute('''CREATE TABLE IF NOT EXISTS price_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  app_id TEXT,
                  name TEXT,
                  discount INTEGER,
                  timestamp DATETIME)''')
    
    # Release tracking table
    c.execute('''CREATE TABLE IF NOT EXISTS releases
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  app_id TEXT,
                  name TEXT,
                  type TEXT,  # 'game', 'dlc'
                  release_date TEXT,
                  is_new BOOLEAN,
                  timestamp DATETIME)''')
    
    # Tracked items table
    c.execute('''CREATE TABLE IF NOT EXISTS tracked_items
                 (app_id TEXT PRIMARY KEY,
                  name TEXT,
                  track_mode TEXT,  # 'release' or 'discount'
                  threshold INTEGER,
                  last_checked DATETIME)''')
    
    # Initialize tracked items from config
    for app_id, game_info in CONFIG['games_to_track'].items():
        c.execute('''INSERT OR IGNORE INTO tracked_items 
                    (app_id, name, track_mode, threshold, last_checked)
                    VALUES (?, ?, ?, ?, ?)''',
                 (app_id, 
                  game_info['name'],
                  game_info.get('track', 'discount'),
                  game_info.get('threshold', 0),
                  datetime.datetime.now()))
    
    conn.commit()
    conn.close()

def get_current_price(app_id):
    """Fetch current discount percentage from SteamDB"""
    url = CONFIG['steam_db_url'].format(app_id=app_id)
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        price_element = soup.select_one('.price-discount')
        if price_element:
            discount_text = price_element.get_text().strip()
            if discount_text != 'Free':
                return int(discount_text.replace('%', '').replace('-', ''))
        return 0
    except Exception as e:
        print(f"Error fetching data for app {app_id}: {e}")
        return None

def check_price_changes():
    """Main function to check for price changes"""
    conn = sqlite3.connect('prices.db')
    c = conn.cursor()
    
    for app_id, game_info in CONFIG['games_to_track'].items():
        current_discount = get_current_price(app_id)
        if current_discount is None:
            continue
            
        # Get previous discount from DB
        c.execute('''SELECT discount FROM price_history 
                     WHERE app_id = ? ORDER BY timestamp DESC LIMIT 1''', (app_id,))
        previous_discount = c.fetchone()
        previous_discount = previous_discount[0] if previous_discount else 0
        
        # Check if discount meets threshold and is new/changed
        if (current_discount >= game_info['threshold'] and 
            current_discount != previous_discount):
            
            game_name = game_info['name']
            store_url = f"https://store.steampowered.com/app/{app_id}"
            
            # Send notifications
            message = (f"🚨 **{game_name}** is now **{current_discount}% off**!\n"
                      f"💸 Previous discount: {previous_discount}%\n"
                      f"🔗 {store_url}")
            
            if CONFIG['email']['enabled']:
                send_email_notification(game_name, current_discount, store_url)
            
            if CONFIG['discord']['enabled']:
                send_discord_notification(message)
        
        # Store in database
        c.execute('''INSERT INTO price_history (app_id, name, discount, timestamp)
                     VALUES (?, ?, ?, ?)''',
                 (app_id, game_info['name'], current_discount, 
                  datetime.datetime.now()))
    
    conn.commit()
    conn.close()

def send_email_notification(game_name, discount, store_url):
    """Send notification via email"""
    msg = EmailMessage()
    msg.set_content(
        f"Steam Price Drop Alert!\n\n"
        f"Game: {game_name}\n"
        f"Discount: {discount}%\n\n"
        f"Check it out: {store_url}"
    )
    msg['Subject'] = f"🎮 {game_name} is {discount}% off on Steam!"
    msg['From'] = CONFIG['email']['sender']
    msg['To'] = CONFIG['email']['receiver']
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(CONFIG['email']['sender'], CONFIG['email']['password'])
            smtp.send_message(msg)
        print(f"Email notification sent for {game_name}")
    except Exception as e:
        print(f"Error sending email: {e}")

def send_discord_notification(message):
    """Send notification via Discord webhook"""
    payload = {
        "content": message,
        "embeds": [{
            "title": "🎮 Steam Discount Alert!",
            "color": 0x00ff00,
            "timestamp": datetime.datetime.now().isoformat()
        }]
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(
            CONFIG['discord']['webhook_url'],
            data=json.dumps(payload),
            headers=headers
        )
        if response.status_code != 204:
            print(f"Discord webhook error: {response.status_code} - {response.text}")
        else:
            print("Discord notification sent successfully")
    except Exception as e:
        print(f"Error sending Discord notification: {e}")

def check_release_status(app_id):
    """Check if an app has been released using Steam API"""
    url = CONFIG['steam']['app_details_url'].format(app_id=app_id)
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = response.json()
        
        if str(app_id) in data and 'data' in data[str(app_id)]:
            app_data = data[str(app_id)]['data']
            return not app_data.get('coming_soon', True)
        return False
    except Exception as e:
        print(f"Error checking release status for {app_id}: {e}")
        return False

def update_tracking_mode(app_id, new_mode, threshold=0):
    """Update the tracking mode for an app in the database"""
    conn = sqlite3.connect('steam_tracker.db')
    c = conn.cursor()
    
    c.execute('''UPDATE tracked_items 
                SET track_mode = ?, threshold = ?
                WHERE app_id = ?''',
             (new_mode, threshold, app_id))
    
    conn.commit()
    conn.close()
    
    # Also update in-memory config if present
    if app_id in CONFIG['games_to_track']:
        CONFIG['games_to_track'][app_id]['track'] = new_mode
        if new_mode == 'discount':
            CONFIG['games_to_track'][app_id]['threshold'] = threshold

def send_release_notification(app_id, name, release_type, message):
    """Send notification for a new release (game or DLC)"""
    store_url = f"https://store.steampowered.com/app/{app_id}"
    full_message = (
        f"🎉 **{name}** ({release_type}) - {message}\n"
        f"🔗 {store_url}"
    )
    if CONFIG['notification']['email']['enabled']:
        send_email_notification(name, 0, store_url)
    if CONFIG['notification']['discord']['enabled']:
        send_discord_notification(
            full_message,
            "🆕 New Release!",
            CONFIG['notification']['discord']['new_release_color'],
            app_id
        )

def process_releases(url, release_type, cursor):
    """Process new or upcoming releases from a Steam store search page."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.select('.search_result_row')
        for result in results:
            app_id = result.get('data-ds-appid')
            name = result.select_one('.title').get_text(strip=True) if result.select_one('.title') else "Unknown"
            release_date = result.select_one('.search_released').get_text(strip=True) if result.select_one('.search_released') else ""
            # Check if already in releases table
            cursor.execute('SELECT 1 FROM releases WHERE app_id = ? AND release_date = ?', (app_id, release_date))
            if not cursor.fetchone():
                # New release found
                cursor.execute('''INSERT INTO releases (app_id, name, type, release_date, is_new, timestamp)
                                  VALUES (?, ?, ?, ?, ?, ?)''',
                               (app_id, name, release_type, release_date, True, datetime.datetime.now()))
                send_release_notification(app_id, name, release_type, f"Released on {release_date}")
    except Exception as e:
        print(f"Error processing releases from {url}: {e}")

def check_new_releases():
    """Check for newly released games/DLCs and update tracking mode"""
    if not CONFIG['track_new_games'] and not CONFIG['track_upcoming_releases']:
        return
    
    conn = sqlite3.connect('steam_tracker.db')
    c = conn.cursor()
    
    # First check our tracked items that are waiting for release
    c.execute('''SELECT app_id, name FROM tracked_items WHERE track_mode = 'release' ''')
    for app_id, name in c.fetchall():
        if check_release_status(app_id):
            # Game has been released - switch to discount tracking
            update_tracking_mode(app_id, 'discount', 50)  # Default 50% threshold
            send_release_notification(app_id, name, 'game', 'Just released!')
            print(f"Switched {name} ({app_id}) from release tracking to discount tracking")
    
    # Check general new releases (if enabled)
    if CONFIG['track_new_games']:
        process_releases(CONFIG['steam']['new_releases_url'], 'game', c)
    
    # Check upcoming releases (now released)
    if CONFIG['track_upcoming_releases']:
        process_releases(CONFIG['steam']['upcoming_url'], 'upcoming', c)
    
    conn.commit()
    conn.close()

def check_price_changes():
    """Check for price drops on tracked games"""
    conn = sqlite3.connect('steam_tracker.db')
    c = conn.cursor()
    
    # Get all items we should check for discounts
    c.execute('''SELECT app_id, name, threshold FROM tracked_items WHERE track_mode = 'discount' ''')
    for app_id, name, threshold in c.fetchall():
        current_discount = get_current_price(app_id)
        if current_discount is None:
            continue
            
        # Get previous discount from DB
        c.execute('''SELECT discount FROM price_history 
                     WHERE app_id = ? ORDER BY timestamp DESC LIMIT 1''', (app_id,))
        previous_discount = c.fetchone()
        previous_discount = previous_discount[0] if previous_discount else 0
        
        # Check if discount meets threshold and is new/changed
        if (current_discount >= threshold and 
            current_discount != previous_discount):
            
            store_url = f"https://store.steampowered.com/app/{app_id}"
            
            # Send notifications
            message = (f"🚨 **{name}** is now **{current_discount}% off**!\n"
                      f"💸 Previous discount: {previous_discount}%\n"
                      f"🔗 {store_url}")
            
            if CONFIG['notification']['email']['enabled']:
                send_email_notification(name, current_discount, store_url)
            
            if CONFIG['notification']['discord']['enabled']:
                send_discord_notification(
                    message,
                    "💰 Steam Price Drop!",
                    CONFIG['notification']['discord']['price_drop_color'],
                    app_id
                )
        
        # Store in database
        c.execute('''INSERT INTO price_history (app_id, name, discount, timestamp)
                     VALUES (?, ?, ?, ?)''',
                 (app_id, name, current_discount, datetime.datetime.now()))
    
    conn.commit()
    conn.close()

def main():
    """Main function to initialize and schedule tasks"""
    init_db()
    scheduler = BackgroundScheduler()
    
    # Schedule price checks
    scheduler.add_job(
        check_price_changes, 
        'interval', 
        hours=CONFIG['check_interval_hours'],
        next_run_time=datetime.datetime.now()
    )
    
    # Schedule new release checks
    scheduler.add_jout(
        check_new_releases, 
        'interval', 
        hours=1,
        next_run_time=datetime.datetime.now()
    )
    
    scheduler.start()
    
    check_price_changes()
    check_new_releases()
    
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()