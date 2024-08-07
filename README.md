Real Estate Deals 

Introduction
This system automates the scraping, processing, and storage of real estate listings into a Neo4j database. It's designed to assist real estate investors by providing up-to-date property data to facilitate decision-making.

Components Breakdown
main.py - Starting Point
Purpose:
Acts as the entry point for running the scraping application.
Workflow:
Configuration Loading
Calls load_config() to retrieve database and application settings.
Zip Codes Loading
Uses load_zip_codes() to fetch a list of zip codes that the system will target for scraping.
Hunter Initialization
Creates an instance of Hunter with necessary parameters like database credentials and search criteria.
Start Scraping
Executes hunter.startSearch() to begin the data scraping cycle.
Graceful Shutdown
Handles unexpected stops or errors and ensures all resources are cleanly released via hunter.close().
hunter.py - Core Logic
Purpose:
Manages the scraping, data processing, and interactions with the database.
Key Functions:
startSearch()
Continuously initiates the search process across specified zip codes. Manages periodic sleeps and reiterations.
search()
Makes HTTP requests to real estate websites, parses HTML responses, and extracts listing details.
search_site()
Targets specific URLs to fetch and process listings. Manages pagination and data extraction using BeautifulSoup.
update_agents()
Processes and updates agent information in the database.
get_saved_listings()
Retrieves listings from a JSON file to check against newly scraped data for updates.
database_ops.py - Database Interactions
Purpose:
Handles all database operations involving Neo4j, ensuring data is correctly stored and updated.
Key Operations:
send_to_neo4j()
Updates or creates new nodes and relationships in the database based on the extracted data.
close()
Properly closes the database connection after operations are complete.
data_loader.py and data_processing.py - Data Handling
Purpose:
data_loader.py: Manages the initial loading of data such as configurations and zip codes.
data_processing.py: Provides functions for cleaning and processing raw data extracted during scraping.
Key Functions:
normalize_phone_number() (Data Loader)
Standardizes phone numbers to a consistent format.
get_unique_utah_agents() (Data Processing)
Filters and processes agent data to ensure uniqueness and accuracy.
listing.py - Data Model
Purpose:
Defines the structure of a real estate listing, encapsulating all relevant data that needs to be extracted from web pages.
Utility Functions and Helpers
Various small utilities assist in tasks such as JSON serialization (listing_to_dict()), error handling (get_traceback()), and file management.
System Flowchart

[main.py] --> [hunter.py]
   |               |
   |--[Load Configurations]      |--[Start Search Loop]
   |--[Load Zip Codes]           |       |--[Scrape Data]
   |                             |       |--[Process Data]
   |                             |       |--[Update Database]
   `--[Initialize Hunter]        |--[Handle Updates]
                                 |       |--[Check for Off-Market Listings]
                                 `--[Close and Cleanup]
Conclusion
This documentation and mind map offer a thorough understanding of how the real estate scraping system operates from start to finish, detailing the interactions between components and the data flow. The system is designed to be robust, with emphasis on reliability and maintainability.