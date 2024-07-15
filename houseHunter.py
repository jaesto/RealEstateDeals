import requests
import pickle
from bs4 import BeautifulSoup 
import os, sys
import datetime
import time
import traceback
import json
from neo4j import GraphDatabase

sys.setrecursionlimit(5000)

def load_config():
    """Load database configuration from a JSON file with error handling."""
    filename = 'config.json'
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: The configuration file '{filename}' was not found.")
        return None  # Return None or exit, depending on your error handling strategy
    except json.JSONDecodeError:
        print(f"Error: Could not decode the JSON in the file '{filename}'. Check its syntax.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def load_zip_codes():
    filename = 'all_zip_codes.json'  # Correct filename for the zip codes file
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: The file '{filename}' could not be decoded.")
        return []

class Hunter():
    sleepTime = 10 * 60
    pickleFileName = 'SavedListings.pkl'
    currentListings = None
    listingsFound = None
    utahrealestateUrl = r'http://www.utahrealestate.com/search/public.search?accuracy=5&geocoded={0}&box=%257B%2522north%2522%253A40.71271490000001%252C%2522south%2522%253A40.51886100000001%252C%2522east%2522%253A-111.520936%252C%2522west%2522%253A-111.871398%257D&htype=zip&lat=40.6210656&lng=-111.81713739999998&geolocation=Salt+Lake+City%2C+UT+{0}&type=1&listprice1=&listprice2={1}&proptype=1&state=ut&tot_bed1=&tot_bath1=&tot_sqf1={2}&dim_acres1={3}&yearblt1=&cap_garage1=&style=&o_style=4&opens=&accessibility=&o_accessibility=32&page={4}'
    kslUrl = r'https://homes.ksl.com/search/zip/{0}/apartment-complex;multi-family-home;single-family-home;townhome-condo/maxprice/{1}'
    
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.65 Safari/537.31'}

    def __init__(self, neo4j_uri, neo4j_user, neo4j_password, zips, maxPrice, minSqFt, minLotSize):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.zipCodes = zips
        self.maxPrice = maxPrice
        self.minSqFt = minSqFt
        self.minLotSize = minLotSize

    def close(self):
        self.driver.close()

    def startSearch(self):
        totalSearches = 0
        while True:
            totalSearches += 1
            try:
                print(f'search #{totalSearches}')
                self.search()
            except Exception as e:
                print(f'Error with search function: {e}')
                print(self.getTraceBack())
            finally:
                print(f'sleeping for {self.sleepTime} seconds...')
                time.sleep(self.sleepTime)

    def search(self):
        self.currentListings = self.getSavedListings()
        self.listingsFound = []
        
        try:
            for zip in self.zipCodes:
                print(f'Searching ZIP: {zip}')
                
                self.session = requests.Session()
                self.session.get(r'http://www.utahrealestate.com/index/public.index')
                
                self.searchSite(self.utahrealestateUrl, zip, self.getUtahRealEstateListingsFromHTML, self.session, 'URE')
                self.searchKSLListings(zip, self.maxPrice, self.session)
                self.session.close()
                
            self.checkForOffTheMarkets()
        except Exception as e:
            msg = f'Error with search: {e}'
            print(msg)
        finally:
            with open(self.pickleFileName, 'wb') as file:
                pickle.dump(self.currentListings, file)

    def searchSite(self, baseUrl, zip, getListings, session, listing_type):
        page = 1
        while True:
            url = baseUrl.format(zip, self.maxPrice, self.minSqFt, self.minLotSize, page)
            try:
                r = session.get(url, headers=self.headers)
                r.raise_for_status()  # Check for HTTP request errors
            except requests.RequestException as e:
                print(f"Error fetching URL {url}: {e}")
                break

            listings = getListings(r.text)
            if len(listings) == 0:
                break

            for l in listings:
                self.listingsFound.append(l.mls)
                if l.mls in self.currentListings.keys():
                    current = self.currentListings[l.mls]
                    if l.price != current.price:
                        self.sendToNeo4j(l, 'price_change', f'Price change from {current.price} to {l.price}', listing_type)
                        self.currentListings[l.mls] = l
                        print(f'Price change for: {l.mls}')
                else:
                    self.sendToNeo4j(l, 'new_listing', None, listing_type)
                    self.currentListings[l.mls] = l
                    print(f'New property found: {l.mls}')
            page += 1

    def getSavedListings(self):
        if not os.path.exists(self.pickleFileName):
            return {}
        try:
            with open(self.pickleFileName, 'rb') as file:
                return pickle.load(file)
        except (EOFError, pickle.UnpicklingError):
            print("Pickle file is empty or corrupted. Creating a new one.")
            return {}

    def getUtahRealEstateListingsFromHTML(self, htmlText):
        print("Searching URE Listings...")
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

            # Extract agent information
            try:
                agent_info = listTable.find('b', string='Agent:')
                if agent_info:
                    agent_info = agent_info.find_next('a')
                    if agent_info:
                        listing.agent_name = agent_info.text.strip()
                        listing.agent_phone = agent_info.find_next('br').next_sibling.strip()
                    else:
                        listing.agent_name = ""
                        listing.agent_phone = ""
            except (AttributeError, IndexError) as e:
                print(f"Error extracting agent info: {e}")
                listing.agent_name = ""
                listing.agent_phone = ""

            # Extract co-agent information
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

            # Extract broker information
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
                    listing.zip = cityZip[2].strip()[-5:]
                else:
                    addressParts = listTable.h2.span.nextSibling.string.strip().split(', ')
                    listing.address = addressParts[0].replace('  ', ' ')
                    listing.city = addressParts[1]
                    listing.zip = addressParts[2][-5:]
            except (AttributeError, IndexError) as e:
                print(f"Error extracting address: {e}")
                listing.address = ""
                listing.city = ""
                listing.zip = ""

            try:
                listing.sqft = int(listTable.find('p', {'class': 'public-detail-overview'}).string.strip()[-12:-8])
            except (AttributeError, IndexError, ValueError) as e:
                print(f"Error extracting sqft: {e}")
                listing.sqft = 0

            listing.ppsqft = listing.price / listing.sqft if listing.sqft else 0

            try:
                listing.acres = float(listTable.find('p', {'class': 'public-detail-overview-b'}).contents[-1].strip())
            except (AttributeError, IndexError, ValueError) as e:
                print(f"Error extracting acres: {e}")
                listing.acres = 0.0

            try:
                listing.stats = listTable.find('p', {'class': 'public-detail-overview'}).string.strip()
            except AttributeError as e:
                print(f"Error extracting stats: {e}")
                listing.stats = ''

            listing.url = r'http://www.utahrealestate.com/report/public.single.report/report/detailed/listno/{0}/scroll_to/{0}'.format(listing.mls)

            listings.append(listing)

        return listings
    
    def searchKSLListings(self, zip, maxPrice, session):
        print("Searching KSL Listings...")
        try:
            url = self.kslUrl.format(zip, maxPrice)
            print(f"Formatted URL: {url}")
            r = session.get(url, headers=self.headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            print(f"Soup content: {soup.prettify()}")  # This will print the entire parsed HTML content, can be very verbose

            # Adjusting to the correct class based on the provided HTML structure
            listings = soup.find_all('div', class_='GridItem_GridItem__p_4dE Listings_GridItem__VqALV')
            listings_a = soup.find_all('a', href=True)
            listings_h = soup.find_all("a", href=lambda href: href and "/listing/" in href)
            listings_text = soup.find_all('div', string='GridItem_GridItem__p_4dE Listings_GridItem__VqALV')
            print(f"Found {len(listings)} listings.")  # Print the number of listings found
            print(f"Found {len(listings_text)} listings.")
            print(f"Found {len(listings_a)} listings.") 
            print(f"Found {len(listings_h)} listings.") 
            print(listings_h)

            for listing in listings:
                try:
                    href = listing.find('a', class_='GridItem_GridItemLink__YgRXw')['href']
                    listing_url = f'https://homes.ksl.com{href}'
                    print(f"Processing listing URL: {listing_url}")  # Debugging line to see the URL being processed
                    self.getKSLListingDetails(listing_url, session)
                except Exception as e:
                    print(f"Error processing KSL listing: {e}")
                    print(traceback.format_exc())
        except Exception as e:
            print(f"Error fetching KSL listings: {e}")
            print(traceback.format_exc())


    def getKSLListingDetails(self, url, session):
        print("Getting KSL Listings Details...")
        try:
            r = session.get(url, headers=self.headers)
            r.raise_for_status()  # Raise an HTTPError for bad responses
        except requests.RequestException as e:
            print(f"Error fetching KSL listing details from {url}: {e}")
            print(traceback.format_exc())
            return

        try:
            soup = BeautifulSoup(r.text, 'html.parser')
            listing = Listing()
            
            try:
                listing.mls = soup.find('span', class_='PageStats-value').text.strip()
            except AttributeError:
                listing.mls = ""

            try:
                contact_info = soup.find('div', class_='ContactInfo')
                if contact_info:
                    listing.agent_name = contact_info.find('span', class_='ContactName-label').text.strip()
                    listing.agent_phone = contact_info.find('div', class_='ContactName-agencyName').text.strip()
                    listing.broker_name = listing.agent_phone  # Broker info is also in the same div as agent phone
                else:
                    listing.agent_name = ""
                    listing.agent_phone = ""
                    listing.broker_name = ""
            except AttributeError:
                listing.agent_name = ""
                listing.agent_phone = ""
                listing.broker_name = ""

            try:
                address_info = soup.find('h1', class_='Address').find_all('div')
                listing.address = address_info[0].text.strip()
                city_state_zip = address_info[1].text.strip().split(',')
                listing.city = city_state_zip[0]
                state_zip = city_state_zip[1].strip().split()
                listing.state = state_zip[0]
                listing.zip = state_zip[1]
            except (AttributeError, IndexError):
                listing.address = ""
                listing.city = ""
                listing.state = ""
                listing.zip = ""

            try:
                listing.priceStr = soup.find('div', class_='Price').text.strip()
                listing.price = int(listing.priceStr[1:].replace(',', ''))
            except (AttributeError, ValueError):
                listing.priceStr = ""
                listing.price = 0

            try:
                listing.photoUrl = soup.find('div', class_='PhotoViewerPrimaryImage').img['src']
            except AttributeError:
                listing.photoUrl = ""

            try:
                listing.description = soup.find('h2', string='Description').find_next_sibling('div').text.strip()
            except AttributeError:
                listing.description = ""

            stats = soup.find('ul', class_='PageStats-list')
            if stats:
                for stat in stats.find_all('li'):
                    try:
                        label = stat.find('span', class_='PageStats-label').text.strip()
                        value = stat.find('span', class_='PageStats-value').text.strip()
                        if label == 'Listing Number':
                            listing.mls = value
                        elif label == 'Expiration Date':
                            listing.expiration_date = value
                        elif label == 'Page Views':
                            listing.page_views = value
                        elif label == 'Favorited':
                            listing.favorited = value
                        elif label == 'Days Online':
                            listing.days_online = value
                        elif label == 'Days Left':
                            listing.days_left = value
                    except AttributeError:
                        continue
            
            details = soup.find('ul', class_='PropertyDetails-list')
            if details:
                for detail in details.find_all('li'):
                    try:
                        label = detail.find('span', class_='PropertyDetails-listItemLabel').text.strip()
                        value = detail.find('span', class_='PropertyDetails-listItemData').text.strip()
                        setattr(listing, label.replace(' ', '_').lower(), value)
                    except AttributeError:
                        continue

            self.sendToNeo4j(listing, 'new_listing', None, 'KSL')
        except Exception as e:
            print(f"Error processing KSL listing details from {url}: {e}")
            print(traceback.format_exc())

    def sendToNeo4j(self, listing, status, additionalText, listing_type):
        try:
            with self.driver.session() as session:
                query = f"""
                MERGE (l:{listing_type} {{mls: $mls}})
                SET l.price = $price,
                    l.priceStr = $priceStr,
                    l.photoUrl = $photoUrl,
                    l.address = $address,
                    l.city = $city,
                    l.state = $state,
                    l.zip = $zip,
                    l.sqft = $sqft,
                    l.ppsqft = $ppsqft,
                    l.acres = $acres,
                    l.foundDate = $foundDate,
                    l.stats = $stats,
                    l.url = $url,
                    l.status = $status,
                    l.additionalText = $additionalText,
                    l.agentName = $agent_name,
                    l.agentPhone = $agent_phone,
                    l.coAgentName = $co_agent_name,
                    l.coAgentPhone = $co_agent_phone,
                    l.brokerName = $broker_name,
                    l.brokerPhone = $broker_phone,
                    l.expirationDate = $expiration_date,
                    l.pageViews = $page_views,
                    l.favorited = $favorited,
                    l.daysOnline = $days_online,
                    l.daysLeft = $days_left,
                    l.description = $description,
                    l.propertyDetails = $property_details
                """
                session.run(query, mls=listing.mls, price=listing.price, priceStr=listing.priceStr, photoUrl=listing.photoUrl,
                            address=listing.address, city=listing.city, state=listing.state, zip=listing.zip, sqft=listing.sqft,
                            ppsqft=listing.ppsqft, acres=listing.acres, foundDate=listing.foundDate, stats=listing.stats,
                            url=listing.url, status=status, additionalText=additionalText,
                            agent_name=listing.agent_name, agent_phone=listing.agent_phone, 
                            co_agent_name=listing.co_agent_name, co_agent_phone=listing.co_agent_phone,
                            broker_name=listing.broker_name, broker_phone=listing.broker_phone,
                            expiration_date=listing.expiration_date, page_views=listing.page_views,
                            favorited=listing.favorited, days_online=listing.days_online, days_left=listing.days_left,
                            description=listing.description, property_details=json.dumps(listing.property_details))
        except Exception as e:
            print(f"Error sending data to Neo4j: {e}")

    def checkForOffTheMarkets(self):
        print('checking for off the markets...')
        for mls in list(self.currentListings.keys()):
            if mls not in self.listingsFound:
                listing = self.currentListings[mls]
                try:
                    timeOnMarket = (datetime.datetime.now() - datetime.datetime.fromtimestamp(listing.foundDate)).days
                except Exception as e:
                    print(f"Error calculating time on market: {e}")
                    timeOnMarket = '???'
                try:
                    self.sendToNeo4j(listing, 'off_market', f'Listing Off Market in {timeOnMarket} days!!!', 'URE')
                except Exception as e:
                    print(f"Error sending off-market listing to Neo4j: {e}")
                del self.currentListings[mls]

    def getTraceBack(self):
        try:
            tb = sys.exc_info()[2]
            pymsg = traceback.format_tb(tb)[0]
        
            if sys.exc_type:
                pymsg = pymsg + "\n" + str(sys.exc_type) + ": " + str(sys.exc_value)
        
            return pymsg
        except Exception as e:
            return f'Problem getting traceback object: {e}'


class Listing():
    def __init__(self):
        self.mls = ''
        self.price = 0
        self.priceStr = ''
        self.photoUrl = ''
        self.address = ''
        self.city = ''
        self.state = ''
        self.zip = ''
        self.sqft = 0
        self.ppsqft = 0
        self.acres = 0.0
        self.foundDate = time.mktime(datetime.datetime.now().timetuple())
        self.stats = ''
        self.url = ''
        self.agent_name = ''
        self.agent_phone = ''
        self.co_agent_name = ''
        self.co_agent_phone = ''
        self.broker_name = ''
        self.broker_phone = ''
        self.expiration_date = ''
        self.page_views = 0
        self.favorited = 0
        self.days_online = 0
        self.days_left = 0
        self.description = ''
        self.property_details = {}

def main():
    config = load_config()
    if not config:
        print("Failed to load configuration. Exiting.")
        return

    zipCodes = load_zip_codes()
    if not zipCodes:
        print("Failed to load zip codes. Exiting.")
        return

    hunter = Hunter(
        neo4j_uri=config['neo4j_uri'],
        neo4j_user=config['neo4j_user'],
        neo4j_password=config['neo4j_password'],
        zips=zipCodes,
        maxPrice=500000,
        minSqFt=1000,
        minLotSize=0.1
    )

    try:
        hunter.startSearch()
    except KeyboardInterrupt:
        print("Search interrupted by user.")
    finally:
        hunter.close()

if __name__ == "__main__":
    main()