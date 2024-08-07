# import requests
# from bs4 import BeautifulSoup
# from listing import Listing
# from data_loader import normalize_phone_number, load_astro_agents
# from data_processing import get_unique_utah_agents, update_city_tags
# from database_ops import DatabaseOps
# import json
# import time
# import datetime
# import traceback
# import csv
# import os, sys
# import pandas as pd

# class Hunter():
#     sleepTime = 30 * 60
#     jsonFileName = 'SavedListings.json'
#     currentListings = None
#     listingsFound = None
#     utahrealestateUrl = r'http://www.utahrealestate.com/search/public.search?accuracy=5&geocoded={0}&box=%257B%2522north%2522%253A40.71271490000001%252C%2522south%2522%253A40.51886100000001%252C%2522east%2522%253A-111.520936%252C%2522west%2522%253A-111.871398%257D&htype=zip&lat=40.6210656&lng=-111.81713739999998&geolocation=Salt+Lake+City%2C+UT+{0}&type=1&listprice1=&listprice2={1}&proptype=1&state=ut&tot_bed1=&tot_bath1=&tot_sqf1={2}&dim_acres1={3}&yearblt1=&cap_garage1=&style=&o_style=4&opens=&accessibility=&o_accessibility=32&page={4}'
#     kslUrl = r'https://homes.ksl.com/search/zip/{0}/apartment-complex;multi-family-home;single-family-home;townhome-condo/maxprice/{1}'
    
#     headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.65 Safari/537.31'}

#     def __init__(self, neo4j_uri, neo4j_user, neo4j_password, zips, maxPrice, minSqFt, minLotSize):
#         self.db_ops = DatabaseOps(neo4j_uri, neo4j_user, neo4j_password)
#         self.zipCodes = zips
#         self.maxPrice = maxPrice
#         self.minSqFt = minSqFt
#         self.minLotSize = minLotSize

#     def close(self):
#         self.db_ops.close()

#     def startSearch(self):
#         totalSearches = 0
#         while True:
#             totalSearches += 1
#             try:
#                 print(f'search #{totalSearches}')
#                 self.search()
#                 self.update_agents()  # Call update_agents after each search
#             except Exception as e:
#                 print(f'Error with search function: {e}')
#                 print(self.get_traceback())
#             finally:
#                 print(f'Completed search #{totalSearches}.')
#                 print(f'sleeping for {self.sleepTime} seconds...')
#                 time.sleep(self.sleepTime)

#     def search(self):
#         self.currentListings = self.get_saved_listings()
#         self.listingsFound = []
        
#         try:
#             for zip in self.zipCodes:
#                 self.session = requests.Session()
#                 self.session.get(r'http://www.utahrealestate.com/index/public.index')
                
#                 self.search_site(self.utahrealestateUrl, zip, self.get_utah_real_estate_listings_from_html, self.session, 'URE')
#                 self.session.close()
            
#             self.check_for_off_the_markets()

#             # Save listings to CSV
#             try:
#                 self.save_listings_to_csv(self.currentListings.values(), 'listings.csv')
#             except Exception as e:
#                 print(f"Error saving listings to CSV: {e}")
#                 print(traceback.format_exc())
#         except Exception as e:
#             msg = f'Error with search: {e}'
#             print(msg)
#             print(traceback.format_exc())
#         finally:
#             print("Entering the 'finally' block.")
#             print(f"self.currentListings has {len(self.currentListings)} items.")
#             try:
#                 print(f"Opening file {self.jsonFileName} for writing...")
#                 with open(self.jsonFileName, 'w') as file:
#                     print("File opened successfully.")
#                     print("Attempting to write JSON file...")
                    
#                     try:
#                         json.dump(self.currentListings, file, default=self.listing_to_dict, indent=4)
#                         print("JSON file written successfully.")
#                     except Exception as e:
#                         print(f"JSON error: {e}")
#                         print(traceback.format_exc())
#                         with open("json_error_debug.log", "w") as debug_file:
#                             debug_file.write(f"JSON error: {e}\n")
#                             for listing in self.currentListings.values():
#                                 debug_file.write(f"{listing}\n")
#                             print("Error details written to json_error_debug.log.")
#             except Exception as e:
#                 print(f"Error writing JSON file '{self.jsonFileName}': {e}")
#                 print(traceback.format_exc())

#     def search_site(self, baseUrl, zip, getListings, session, listing_type):
#         page = 1
#         while True:
#             url = baseUrl.format(zip, self.maxPrice, self.minSqFt, self.minLotSize, page)
#             try:
#                 r = session.get(url, headers=self.headers)
#                 r.raise_for_status()  # Check for HTTP request errors
#             except requests.RequestException as e:
#                 print(f"Error fetching URL {url}: {e}")
#                 break

#             listings = getListings(r.text)
#             if len(listings) == 0:
#                 break

#             for l in listings:
#                 self.listingsFound.append(l.mls)
#                 if l.mls in self.currentListings.keys():
#                     current = self.currentListings[l.mls]
#                     if l.price != current.price:
#                         self.check_price_change_percentage(current, l)
#                         self.db_ops.send_to_neo4j(l, 'price_change', f'Price change from {current.price} to {l.price}', 'URE')
#                         self.currentListings[l.mls] = l
#                         print(f'Price change for: {l.mls}')
#                 else:
#                     self.db_ops.send_to_neo4j(l, 'new_listing', None, listing_type)
#                     self.currentListings[l.mls] = l
#             page += 1

#     def get_scrapped_agents(self):
#         scrapped_agents = pd.DataFrame([{
#             'First Name': listing.agent_first_name,
#             'Last Name': listing.agent_last_name,
#             'Phone': normalize_phone_number(listing.agent_phone),
#             'City': listing.city
#         } for listing in self.currentListings.values() if listing.agent_phone])
#         return scrapped_agents

#     def update_agents(self):
#         # Load astro agents
#         astro_agents = load_astro_agents('contacts.csv')
#         if astro_agents.empty:
#             print("No astro agents loaded. Exiting.")
#             return

#         # Get scrapped agents
#         scrapped_agents = self.get_scrapped_agents()

#         # Ensure the columns are strings
#         scrapped_agents['First Name'] = scrapped_agents['First Name'].astype(str)
#         scrapped_agents['Last Name'] = scrapped_agents['Last Name'].astype(str)

#         # Get unique Utah agents
#         unique_utah_agents = get_unique_utah_agents(astro_agents, scrapped_agents)

#         # Save unique Utah agents to a CSV file
#         unique_utah_agents.to_csv('unique_utah_agents.csv', index=False)
#         print("Unique Utah agents saved to 'unique_utah_agents.csv'.")

#         # Update city tags
#         update_city_tags('unique_utah_agents.csv', 'unique_utah_agents_updated.csv')

#     def check_price_change_percentage(self, old_listing, new_listing):
#         old_price = old_listing.price
#         new_price = new_listing.price
#         change_percentage = ((new_price - old_price) / old_price) * 100
#         new_listing.price_change_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         new_listing.price_change_percentage = change_percentage
#         print(f"Price change: {old_price} -> {new_price} ({change_percentage:.2f}%) on {new_listing.price_change_date}")
#         # You can add more logic here based on the percentage change if needed

#     def get_saved_listings(self):
#         if not os.path.exists(self.jsonFileName):
#             print("JSON file does not exist. Creating a new one.")
#             return {}
#         try:
#             with open(self.jsonFileName, 'r') as file:
#                 data = json.load(file)
#                 return {mls: Listing.from_dict(details) for mls, details in data.items()}
#         except (json.JSONDecodeError, FileNotFoundError) as e:
#             print(f"JSON file is empty or corrupted: {e}. Creating a new one.")
#             return {}
#         except Exception as e:
#             print(f"Unexpected error while loading JSON file: {e}")
#             return {}

#     def listing_to_dict(self, obj):
#         if isinstance(obj, Listing):
#             return obj.__dict__
#         return obj

#     def get_utah_real_estate_listings_from_html(self, htmlText):
#         soup = BeautifulSoup(htmlText, 'html.parser')
#         listings = []
#         for listTable in soup.findAll('table', {'class': 'public-detail-quickview'}):
#             listing = Listing()
#             try:
#                 listing.mls = listTable.find('p', {'class': 'public-detail-overview-b'}).contents[2].strip()
#             except (AttributeError, IndexError) as e:
#                 print(f"Error extracting MLS: {e}")
#                 listing.mls = ''

#             try:
#                 listing.priceStr = listTable.h2.span.string
#                 listing.price = int(listing.priceStr[1:].replace(',', ''))
#             except (AttributeError, IndexError, ValueError) as e:
#                 print(f"Error extracting price: {e}")
#                 listing.priceStr = ''
#                 listing.price = 0

#             try:
#                 listing.photoUrl = listTable.img['src']
#             except (AttributeError, IndexError) as e:
#                 print(f"Error extracting photo URL: {e}")
#                 listing.photoUrl = ''

#             try:
#                 agent_info = listTable.find('b', string='Agent:')
#                 if agent_info:
#                     agent_info = agent_info.find_next('a')
#                     if agent_info:
#                         listing.agent_name = agent_info.text.strip()
#                         listing.agent_phone = agent_info.find_next('br').next_sibling.strip()
#                         if listing.agent_name:
#                             name_parts = listing.agent_name.split()
#                             listing.agent_first_name = name_parts[0]
#                             listing.agent_last_name = ' '.join(name_parts[1:])
#                         else:
#                             listing.agent_first_name = ""
#                             listing.agent_last_name = ""
#                     else:
#                         listing.agent_name = ""
#                         listing.agent_phone = ""
#                         listing.agent_first_name = ""
#                         listing.agent_last_name = ""
#             except (AttributeError, IndexError) as e:
#                 print(f"Error extracting agent info: {e}")
#                 listing.agent_name = ""
#                 listing.agent_phone = ""
#                 listing.agent_first_name = ""
#                 listing.agent_last_name = ""

#             try:
#                 co_agent_info = listTable.find('b', string='Co-Agent:')
#                 if co_agent_info:
#                     co_agent_info = co_agent_info.find_next('a')
#                     if co_agent_info:
#                         listing.co_agent_name = co_agent_info.text.strip()
#                         listing.co_agent_phone = co_agent_info.find_next('br').next_sibling.strip()
#                     else:
#                         listing.co_agent_name = ""
#                         listing.co_agent_phone = ""
#             except (AttributeError, IndexError) as e:
#                 print(f"Error extracting co-agent info: {e}")
#                 listing.co_agent_name = ""
#                 listing.co_agent_phone = ""

#             try:
#                 broker_info = listTable.find('b', string='Office:')
#                 if broker_info:
#                     broker_info = broker_info.find_next('a')
#                     if broker_info:
#                         listing.broker_name = broker_info.text.strip()
#                         listing.broker_phone = broker_info.find_next('br').next_sibling.strip()
#                     else:
#                         listing.broker_name = ""
#                         listing.broker_phone = ""
#             except (AttributeError, IndexError) as e:
#                 print(f"Error extracting broker info: {e}")
#                 listing.broker_name = ""
#                 listing.broker_phone = ""

#             try:
#                 if listTable.h2.i:
#                     listing.address = listTable.h2.i.string.replace('  ', ' ')
#                     cityZip = listTable.h2.i.nextSibling.string.split(', ')
#                     listing.city = cityZip[1]
#                     listing.state = cityZip[2].split()[0]
#                     listing.zip = cityZip[2].strip()[-5:]
#                 else:
#                     addressParts = listTable.h2.span.nextSibling.string.strip().split(', ')
#                     listing.address = addressParts[0].replace('  ', ' ')
#                     listing.city = addressParts[1]
#                     listing.state = addressParts[2].split()[0]
#                     listing.zip = addressParts[2][-5:]
#             except (AttributeError, IndexError) as e:
#                 print(f"Error extracting address for listing with MLS {listing.mls}: {e}")
#                 listing.address = ""
#                 listing.city = ""
#                 listing.state = ""
#                 listing.zip = ""

#             try:
#                 listing.sqft = int(listTable.find('p', {'class': 'public-detail-overview'}).string.strip()[-12:-8])
#             except (AttributeError, IndexError, ValueError) as e:
#                 print(f"Error extracting sqft for listing with MLS {listing.mls}: {e}")
#                 listing.sqft = 0

#             listing.ppsqft = listing.price / listing.sqft if listing.sqft else 0

#             try:
#                 listing.acres = float(listTable.find('p', {'class': 'public-detail-overview-b'}).contents[-1].strip())
#             except (AttributeError, IndexError, ValueError) as e:
#                 print(f"Error extracting acres for listing with MLS {listing.mls}: {e}")
#                 listing.acres = 0.0

#             try:
#                 listing.stats = listTable.find('p', {'class': 'public-detail-overview'}).string.strip()
#             except AttributeError as e:
#                 print(f"Error extracting stats for listing with MLS {listing.mls}: {e}")
#                 listing.stats = ''

#             listing.url = r'http://www.utahrealestate.com/report/public.single.report/report/detailed/listno/{0}/scroll_to/{0}'.format(listing.mls)

#             listings.append(listing)

#         return listings

#     def save_listings_to_csv(self, listings, filename='listings.csv'):
#         try:
#             with open(filename, mode='w', newline='', encoding='utf-8') as file:
#                 writer = csv.writer(file)
#                 writer.writerow([
#                     'Property Address', 'Property City', 'Property State', 
#                     'Property Zipcode', 'First Name', 'Last Name', 'Email', 'Phone'
#                 ])
#                 for listing in listings:
#                     writer.writerow([
#                         listing.address, listing.city, listing.state, listing.zip, 
#                         listing.agent_first_name, listing.agent_last_name, 
#                         '',  # set email as empty string
#                         listing.agent_phone
#                     ])
#             print(f"CSV file '{filename}' written successfully.")
#         except Exception as e:
#             print(f"Error writing CSV file '{filename}': {e}")
    
#     def check_for_off_the_markets(self):
#         print('checking for off the markets...')
#         for mls in list(self.currentListings.keys()):
#             if mls not in self.listingsFound:
#                 listing = self.currentListings[mls]
#                 print(f"Listing {mls} not found in current search. Marking as off the market.")
#                 try:
#                     timeOnMarket = (datetime.datetime.now() - datetime.datetime.fromtimestamp(listing.foundDate)).days
#                 except Exception as e:
#                     print(f"Error calculating time on market: {e}")
#                     timeOnMarket = '???'
#                 try:
#                     self.db_ops.send_to_neo4j(listing, 'off_market', f'Listing Off Market in {timeOnMarket} days!!!', 'URE')
#                     print(f"Listing {mls} marked as off the market in Neo4j.")
#                 except Exception as e:
#                     print(f"Error sending off-market listing to Neo4j: {e}")
#                 del self.currentListings[mls]
#                 print(f"Listing {mls} removed from current listings.")
#         print('Completed checking for off the markets.')

#     def get_traceback(self):
#         try:
#             tb = sys.exc_info()[2]
#             pymsg = traceback.format_tb(tb)[0]
        
#             if sys.exc_type:
#                 pymsg = pymsg + "\n" + str(sys.exc_type) + ": " + str(sys.exc_value)
        
#             return pymsg
#         except Exception as e:
#             return f'Problem getting traceback object: {e}'
