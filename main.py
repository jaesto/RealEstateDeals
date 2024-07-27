from hunter import Hunter
from config import load_config
from data_loader import load_zip_codes

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
        maxPrice=750000,
        minSqFt=750,
        minLotSize=0.01
    )

    try:
        hunter.startSearch()
    except KeyboardInterrupt:
        print("Search interrupted by user.")
    finally:
        hunter.close()

if __name__ == "__main__":
    main()
