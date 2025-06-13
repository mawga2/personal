import concurrent.futures
import urllib.request
import csv
from bs4 import BeautifulSoup

def scrape(url):
    try:
        req = urllib.request.urlopen(url)
        html = req.read()
    except Exception as e:
        # If there is an error while opening the URL, return None
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
    
    # Find the first purchase div (base game)
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
        # Check if it's an upcoming game (e.g., "Coming Soon")
        coming_soon = soup.find('div', {'class': 'comingsoon'})
        if coming_soon:
            price = "Coming Soon"

    return (title, developer, publisher, tags, user_review, price, discount_pct, url)
    
    # # Initialize the user review variable
    # user_review = "No reviews"
    
    # # Find all the spans with the class 'game_review_summary'
    # review_spans = soup.find_all('span', {'class': 'game_review_summary'})
    
    # # Loop through the review spans and get the text of the first one
    # for review_span in review_spans:
    #     user_review = review_span.text.strip()
    #     break

    # # Check if the user review indicates no reviews or if it's the default value
    # if "No user reviews" in user_review or " user reviews" in user_review or user_review == "No reviews":
    #     return None
    
    # # Find the title div with the class 'apphub_AppName' and id 'appHubAppName_responsive'
    # title_div = soup.find('div', {'class': 'apphub_AppName'}, id='appHubAppName_responsive')
    
    # # If the title div is not found, return None
    # if not title_div:
    #     return None
    
    # # Get the title by stripping the text from the title div
    # title = title_div.text.strip()
    
    # # # Check if the title contains "Soundtrack" or "DLC"
    # # if "Soundtrack" in title or "DLC" in title:
    # #     return None

    # # Initialize the developer and publisher variables
    # developer = "No Developer"
    # publisher = "No Publisher"
    
    # # Find all the divs with the class 'dev_row'
    # devpub = soup.find_all('div', {'class': 'dev_row'})
    
    # # If devpub is not empty
    # if devpub:
    #     # Check if there are at least two elements in devpub
    #     if len(devpub) > 1:
    #         # Get the developer name from the first 'a' tag in the first devpub div
    #         developer = devpub[0].find_all('a')[0].text.strip()
            
    #         # Get the publisher name from the first 'a' tag in the second devpub div
    #         publisher = devpub[1].find_all('a')[0].text.strip()

    # # Initialize the tags list
    # tags = []
    
    # # Find all the 'a' tags with the class 'app_tag'
    # tag_list = soup.find_all('a', {'class': 'app_tag'})
    
    # # If tag_list is not empty
    # if tag_list:
    #     # Check if there are at least two elements in tag_list
    #     if len(tag_list) > 1:
    #         # Loop through the tag_list and append the stripped text to the tags list
    #         for tag in tag_list:
    #             tags.append(tag.text.strip())

    # # Initialize the price variable
    # price = "Free"
    
    # # Find the div with the class 'game_purchase_price price'
    # price_div = soup.find('div', {'class': 'game_purchase_price price'})
    
    # # If price_div is found
    # if price_div:
    #     # Check if the stripped text of price_div is not empty
    #     if price_div.text.strip():
    #         # Update the price with the stripped text of price_div
    #         price = price_div.text.strip()

    # # Return a tuple containing the scraped information
    # return (title, developer, publisher, tags, user_review, price, url)

# Open the file containing the list of URLs to scrape
with open('steam_urls.txt', encoding='utf-8') as f, open('steam_games.csv', 'w', newline='', encoding='utf-8') as outfile:
    # Read the URLs from input
    urls = [line.strip() for line in f]
    num_urls = len(urls)

    outfileWriter = csv.writer(outfile)
    outfileWriter.writerow(['title','developer','publisher','tags', 'user_review', 'price', 'discount_pct', 'url'])
    
    # Use a ThreadPoolExecutor to concurrently scrape the URLs
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scrape, url) for url in urls]
        
        # Iterate through the completed futures as they finish
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            result = future.result()
            if result:
                # Unpack the result tuple
                title, developer, publisher, tags, user_review, price, discount_pct, url = result
                row = [title, developer, publisher, tags, user_review, price, discount_pct, url]
                outfileWriter.writerow(row)
                
                # Write the scraped information to the output file
                # outfile.write(f"Title: {title}\n")
                # outfile.write(f"Developer: {developer}\n")
                # outfile.write(f"Publisher: {publisher}\n")
                # outfile.write(f"Tags: {tags}\n")
                # outfile.write(f"User Review Score: {user_review}\n")
                # outfile.write(f"Price: {price}\n")
                # outfile.write(f"URL: {url}\n")
                # outfile.write("--\n")
            
            percentage_complete = (i + 1) / num_urls * 100
            print(f"{percentage_complete:.2f}% complete")