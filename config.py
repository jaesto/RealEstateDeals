import json

def load_config():
    """
    Load configuration settings from a JSON file.

    Returns:
        dict: A dictionary containing configuration settings.
    """
    try:
        with open('config.json', 'r') as file:
            config = json.load(file)
            return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading config file: {e}")
        return None

def load_bama_zip_codes(counties):
    """
    Loads Alabama ZIP codes from the JSON file. Optionally filters by counties.

    Args:
        counties (list): A list of county names to filter ZIP codes.

    Returns:
        list: A list of ZIP codes.
    """
    with open('bama_county_city_zip_codes.json', 'r') as file:
        data = json.load(file)
        
    if counties:
        # Filter ZIP codes by specified counties
        zip_codes = [
            zip_code 
            for county, cities in data.items() 
            if county in counties
            for city, zips in cities.items() 
            for zip_code in zips
        ]
    else:
        # Get all ZIP codes
        zip_codes = [
            zip_code 
            for county, cities in data.items() 
            for city, zips in cities.items() 
            for zip_code in zips
        ]
    
    return zip_codes

