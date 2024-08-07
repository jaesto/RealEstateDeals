# ure_scraping.py
import requests
from bs4 import BeautifulSoup
from listing import Listing

"""
    Searches the site using the provided parameters and processes each listing found.

    Args:
        baseUrl (str): The base URL for the search query.
        zip_code (str): The zip code to search within.
        maxPrice (int): The maximum price to filter listings.
        minSqFt (int): The minimum square footage to filter listings.
        minLotSize (float): The minimum lot size to filter listings.
        getListings (function): A function to extract listings from HTML.
        headers (dict): The headers to use for HTTP requests.
    process_listing_callback (function): A callback function to process each listing.
    """
def search_site(baseUrl, zip_code, maxPrice, minSqFt, minLotSize, getListings, headers, process_listing_callback, total_counter):
    session = requests.Session()
    listings_sent_to_neo4j = 0  # Counter for listings sent to Neo4j
    try:
        page = 1
        while True:
            # print(f"Fetching page {page}")
            url = baseUrl.format(zip_code, maxPrice, minSqFt, minLotSize, page)
            try:
                response = session.get(url, headers=headers)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Error fetching URL {url}: {e}")
                break

            listings = getListings(response.text)
            if not listings:
                # print("No more listings found. Ending search.")
                break

            # print(f"Found {len(listings)} listings on page {page}")
            for listing in listings:
               if process_listing_callback(listing):
                    listings_sent_to_neo4j += 1
                    total_counter[0] += 1


            page += 1  # Proceed to the next page
    finally:
        session.close()

    # print(f"Completed search for ZIP code {zip_code}. Listings sent to Neo4j: {listings_sent_to_neo4j}")
    # print("Completed search.")

def get_utah_real_estate_listings_from_html(htmlText):
    """
    Extracts listings from HTML text.

    Args:
        htmlText (str): The HTML content to parse.

    Returns:
        list: A list of Listing objects extracted from the HTML.
    """
    soup = BeautifulSoup(htmlText, 'html.parser')
    listings = []
    for listTable in soup.findAll('table', {'class': 'public-detail-quickview'}):
        listing = Listing()
        try:
            listing.mls = listTable.find('p', {'class': 'public-detail-overview-b'}).contents[2].strip()
        except (AttributeError, IndexError) as e:
            print(f"Error extracting MLS: {e}")
            listing.mls = ''

        try:
            listing.priceStr = listTable.h2.span.string
            listing.price = int(listing.priceStr[1:].replace(',', ''))
        except (AttributeError, IndexError, ValueError) as e:
            print(f"Error extracting price: {e}")
            listing.priceStr = ''
            listing.price = 0

        try:
            listing.photoUrl = listTable.img['src']
        except (AttributeError, IndexError) as e:
            print(f"Error extracting photo URL: {e}")
            listing.photoUrl = ''

        try:
            agent_info = listTable.find('b', string='Agent:')
            if agent_info:
                agent_info = agent_info.find_next('a')
                if agent_info:
                    listing.agent_name = agent_info.text.strip()
                    listing.agent_phone = agent_info.find_next('br').next_sibling.strip()
                    if listing.agent_name:
                        name_parts = listing.agent_name.split()
                        listing.agent_first_name = name_parts[0]
                        listing.agent_last_name = ' '.join(name_parts[1:])
                    else:
                        listing.agent_first_name = ""
                        listing.agent_last_name = ""
                else:
                    listing.agent_name = ""
                    listing.agent_phone = ""
                    listing.agent_first_name = ""
                    listing.agent_last_name = ""
        except (AttributeError, IndexError) as e:
            print(f"Error extracting agent info: {e}")
            listing.agent_name = ""
            listing.agent_phone = ""
            listing.agent_first_name = ""
            listing.agent_last_name = ""

        try:
            co_agent_info = listTable.find('b', string='Co-Agent:')
            if co_agent_info:
                co_agent_info = co_agent_info.find_next('a')
                if co_agent_info:
                    listing.co_agent_name = co_agent_info.text.strip()
                    listing.co_agent_phone = co_agent_info.find_next('br').next_sibling.strip()
                else:
                    listing.co_agent_name = ""
                    listing.co_agent_phone = ""
        except (AttributeError, IndexError) as e:
            print(f"Error extracting co-agent info: {e}")
            listing.co_agent_name = ""
            listing.co_agent_phone = ""

        try:
            broker_info = listTable.find('b', string='Office:')
            if broker_info:
                broker_info = broker_info.find_next('a')
                if broker_info:
                    listing.broker_name = broker_info.text.strip()
                    listing.broker_phone = broker_info.find_next('br').next_sibling.strip()
                else:
                    listing.broker_name = ""
                    listing.broker_phone = ""
        except (AttributeError, IndexError) as e:
            print(f"Error extracting broker info: {e}")
            listing.broker_name = ""
            listing.broker_phone = ""

        try:
            if listTable.h2.i:
                listing.address = listTable.h2.i.string.replace('  ', ' ')
                cityZip = listTable.h2.i.nextSibling.string.split(', ')
                listing.city = cityZip[1]
                listing.state = cityZip[2].split()[0]
                listing.zip = cityZip[2].strip()[-5:]
            else:
                addressParts = listTable.h2.span.nextSibling.string.strip().split(', ')
                listing.address = addressParts[0].replace('  ', ' ')
                listing.city = addressParts[1]
                listing.state = addressParts[2].split()[0]
                listing.zip = addressParts[2][-5:]
        except (AttributeError, IndexError) as e:
            print(f"Error extracting address for listing with MLS {listing.mls}: {e}")
            listing.address = ""
            listing.city = ""
            listing.state = ""
            listing.zip = ""

        try:
            listing.sqft = int(listTable.find('p', {'class': 'public-detail-overview'}).string.strip()[-12:-8])
        except (AttributeError, IndexError, ValueError) as e:
            print(f"Error extracting sqft for listing with MLS {listing.mls}: {e}")
            listing.sqft = 0

        listing.ppsqft = listing.price / listing.sqft if listing.sqft else 0

        try:
            listing.acres = float(listTable.find('p', {'class': 'public-detail-overview-b'}).contents[-1].strip())
        except (AttributeError, IndexError, ValueError) as e:
            print(f"Error extracting acres for listing with MLS {listing.mls}: {e}")
            listing.acres = 0.0

        try:
            listing.stats = listTable.find('p', {'class': 'public-detail-overview'}).string.strip()
        except AttributeError as e:
            print(f"Error extracting stats for listing with MLS {listing.mls}: {e}")
            listing.stats = ''

        listing.url = r'http://www.utahrealestate.com/report/public.single.report/report/detailed/listno/{0}/scroll_to/{0}'.format(listing.mls)

        listings.append(listing)

    return listings
