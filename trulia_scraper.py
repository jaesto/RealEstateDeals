import requests
from bs4 import BeautifulSoup
from listing import Listing
from database_ops import DatabaseOps

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.65 Safari/537.31'
}

def fetch_listings(url):
    """
    Fetches the HTML content from the given URL.

    Args:
        url (str): The URL to fetch the content from.

    Returns:
        BeautifulSoup: The parsed HTML content.
    """
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    except requests.RequestException as e:
        print(f"Error fetching the URL {url}: {e}")
        return None

def extract_listing_urls(soup):
    """
    Extracts listing URLs from the search results page.

    Args:
        soup (BeautifulSoup): The parsed HTML content.

    Returns:
        list: A list of listing URLs.
    """
    listings = []
    try: 
        for link in soup.find_all('a', {'data-testid': 'property-card-link'}):
            full_url = "https://www.trulia.com" + link['href']
            print(full_url)
            listings.append(full_url)
            print(f"Found listing URL: {full_url}")
        return listings
    except Exception as e:
        print(f"Error extracting href from {full_url}: {e}")

def extract_listing_details(url):
    """
    Extracts details from a listing page.

    Args:
        url (str): The URL of the listing page.

    Returns:
        Listing: A Listing object containing the extracted details.
    """
    listing = Listing()
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract MLS ID
        mls_tag = soup.find('span', {'data-testid': 'hdp-mls-id'})
        listing.mls = mls_tag.text.strip() if mls_tag else 'N/A'

        # Extract price
        price_tag = soup.find('div', {'data-testid': 'on-market-price-details'})
        listing.priceStr = price_tag.text.strip() if price_tag else 'N/A'
        listing.price = int(listing.priceStr.replace('$', '').replace(',', ''))

        # Extract address and ensure state is not hardcoded
        address_tag = soup.find('span', {'data-testid': 'home-details-summary-city-state'})
        if address_tag:
            address_parts = address_tag.text.strip().split(',')
            listing.address = ', '.join(address_parts[:-1]).strip()
            listing.city = address_parts[0].strip()
            listing.state = address_parts[-1].strip().split()[-1]  # Now extracting state from address
            listing.zip = address_parts[-1].strip().split()[-1]

        # Extract agent and broker information
        agent_info = soup.find('div', text=lambda text: 'Listing courtesy' in text if text else False)
        if agent_info:
            agent_details = agent_info.next_sibling.text.strip().split(',')
            listing.agent_name = agent_details[0].strip()
            listing.agent_phone = agent_details[1].strip()

        broker_info = agent_info.find_next('div', class_='broker-info')
        if broker_info:
            listing.broker_name = broker_info.text.strip()

        co_agent_info = broker_info.find_next_sibling('div') if broker_info else None
        if co_agent_info and 'Co-Agent' in co_agent_info.text:
            co_agent_details = co_agent_info.text.strip().split(',')
            listing.co_agent_name = co_agent_details[0].replace('Co-Agent:', '').strip()
            listing.co_agent_phone = co_agent_details[1].strip() if len(co_agent_details) > 1 else ''

        # Extract additional details (e.g., beds, baths, sqft)
        details_tag = soup.find('div', {'data-testid': 'home-details-summary-features'})
        if details_tag:
            details = details_tag.text.strip().split('•')
            for detail in details:
                if 'bed' in detail.lower():
                    listing.beds = int(detail.split()[0])
                elif 'bath' in detail.lower():
                    listing.baths = float(detail.split()[0])
                elif 'sqft' in detail.lower():
                    listing.sqft = int(detail.replace('sqft', '').replace(',', '').strip())

        return listing
    except requests.RequestException as e:
        print(f"Error fetching the URL {url}: {e}")
        return None
    except Exception as e:
        print(f"Error extracting details from {url}: {e}")
        return None

def scrape_trulia(zip_code, db_ops, max_price):
    """
    Scrapes the listings for a given ZIP code from Trulia and stores them in the database.

    Args:
        zip_code (str): The ZIP code to scrape listings for.
        db_ops (DatabaseOps): The database operations instance.
    """
    url = f'https://www.trulia.com/for_sale/{zip_code}_zip/0-{max_price}_price/APARTMENT,CONDO,COOP,MULTI-FAMILY,SINGLE-FAMILY_HOME,TOWNHOUSE,UNKNOWN_type/'
    print(url)
    soup = fetch_listings(url)
    if not soup:
        print("nothing is soup")
        return

    listing_urls = extract_listing_urls(soup)
    for listing_url in listing_urls:
        listing = extract_listing_details(listing_url)
        if listing:
            db_ops.send_to_neo4j(listing, 'new_listing', None, 'TRULIA')
            print(f"Listing sent to Neo4j: {listing.mls}")

