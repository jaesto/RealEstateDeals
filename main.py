import time
import json
import os
from ure_scraping import search_site, get_utah_real_estate_listings_from_html
from database_ops import DatabaseOps
from agent_manager import AgentManager
from listing import Listing
from utils import get_traceback
# from hunter import Hunter
from config import load_config, load_bama_zip_codes
from data_loader import load_zip_codes
from trulia_scraper import scrape_trulia

def process_listing(listing, currentListings, db_ops):
    """
    Processes a single listing and updates it in the database.

    Args:
        listing (Listing): The listing to process.
        currentListings (dict): The dictionary of current listings.
        db_ops (DatabaseManager): The database manager instance.
    """
    sent_to_neo4j = False
    if listing.mls in currentListings:
        current = currentListings[listing.mls]
        if listing.price != current.price:
            check_price_change_percentage(current, listing)
            db_ops.send_to_neo4j(listing, 'price_change', f'Price change from {current.price} to {listing.price}', 'URE')
            currentListings[listing.mls] = listing
            print(f'Price change for: {listing.mls}')
            sent_to_neo4j = True
    else:
        db_ops.send_to_neo4j(listing, 'new_listing', None, 'URE')
        currentListings[listing.mls] = listing
        sent_to_neo4j = True

    return sent_to_neo4j

def check_price_change_percentage(old_listing, new_listing):
    """
    Calculates the price change percentage and updates the listing.

    Args:
        old_listing (Listing): The old listing object.
        new_listing (Listing): The new listing object.
    """
    old_price = old_listing.price
    new_price = new_listing.price
    change_percentage = ((new_price - old_price) / old_price) * 100
    new_listing.price_change_date = time.strftime("%Y-%m-%d %H:%M:%S")
    new_listing.price_change_percentage = change_percentage
    print(f"Price change: {old_price} -> {new_price} ({change_percentage:.2f}%) on {new_listing.price_change_date}")

def get_saved_listings(jsonFileName):
    """
    Loads saved listings from a JSON file.

    Args:
        jsonFileName (str): The filename of the JSON file.

    Returns:
        dict: A dictionary of saved listings.
    """
    if not os.path.exists(jsonFileName):
        print("JSON file does not exist. Creating a new one.")
        return {}
    try:
        with open(jsonFileName, 'r') as file:
            data = json.load(file)
            return {mls: Listing.from_dict(details) for mls, details in data.items()}
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"JSON file is empty or corrupted: {e}. Creating a new one.")
        return {}
    except Exception as e:
        print(f"Unexpected error while loading JSON file: {e}")
        return {}

def main():
    config = load_config()
    if not config:
        print("Failed to load configuration. Exiting.")
        return

    zipCodes = load_zip_codes()
    if not zipCodes:
        print("Failed to load zip codes. Exiting.")
        return

    db_ops = DatabaseOps(
        uri=config['neo4j_uri'],
        user=config['neo4j_user'],
        password=config['neo4j_password']
    )

    agent_manager=AgentManager('contacts.csv')
    jsonFileName='SavedListings.json'
    currentListings=get_saved_listings(jsonFileName)
    ureURL=config['utahrealestateUrl']
    sleep_time=config['sleepTime']
    total_listings_sent_to_neo4j = [0] 

    # Load Alabama ZIP codes, optionally filtering by counties
    counties_to_search = ['Madison', 'Huntsville']  # Specify the counties you want
    alabama_zip_codes = load_bama_zip_codes(counties=counties_to_search)
    

    try:
        totalSearches = 0
        while True:
            totalSearches += 1
            print(f'Search #{totalSearches}')
            try:
                for zip_code in zipCodes:
                    search_site(
                        baseUrl=ureURL,
                        zip_code=zip_code,
                        maxPrice=15000000,
                        minSqFt=750,
                        minLotSize=0.01,
                        getListings=get_utah_real_estate_listings_from_html,
                        headers=config['headers'],
                        process_listing_callback=lambda listing: process_listing(listing, currentListings, db_ops),
                        total_counter=total_listings_sent_to_neo4j 
                    )

                # Scrape listings from Trulia for each ZIP code
                for zip_code in alabama_zip_codes:
                    scrape_trulia(zip_code, db_ops, 350000)

                agent_manager.update_agents(currentListings)
            except Exception as e:
                print(f"Error during search cycle: {e}")
                print(get_traceback())
            finally:
                save_listings_to_json(currentListings, jsonFileName)
                print(f"Total listings sent to Neo4j across all searches: {total_listings_sent_to_neo4j[0]}")       
                print(f'Completed search #{totalSearches}. Sleeping for {sleep_time} seconds...')
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        print("Search interrupted by user.")
    finally:
        db_ops.close()

def save_listings_to_json(listings, jsonFileName):
    """
    Saves listings to a JSON file.

    Args:
        listings (dict): A dictionary of listings.
        jsonFileName (str): The filename of the JSON file.
    """
    print("Entering the 'finally' block.")
    print(f"currentListings has {len(listings)} items.")
    try:
        print(f"Opening file {jsonFileName} for writing...")
        with open(jsonFileName, 'w') as file:
            print("File opened successfully.")
            print("Attempting to write JSON file...")
            
            try:
                json.dump(listings, file, default=lambda obj: obj.__dict__, indent=4)
                print("JSON file written successfully.")
            except Exception as e:
                print(f"JSON error: {e}")
                with open("json_error_debug.log", "w") as debug_file:
                    debug_file.write(f"JSON error: {e}\n")
                    for listing in listings.values():
                        debug_file.write(f"{listing}\n")
                    print("Error details written to json_error_debug.log.")
    except Exception as e:
        print(f"Error writing JSON file '{jsonFileName}': {e}")

if __name__ == "__main__":
    main()
