import requests
from bs4 import BeautifulSoup
import json

def fetch_utah_zip_codes(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.65 Safari/537.31'}
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()  # Check for HTTP request errors
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None
    try:
        zipPage = BeautifulSoup(r.text, 'html.parser')
        countyZipCodes = zipPage.find('table', {'class': 'countyZipCodes'})
        if not countyZipCodes:
            raise ValueError("Could not find the table with class 'countyZipCodes'")
    except Exception as e:
        print(f"Error parsing the HTML: {e}")
        return None
    return countyZipCodes

def extract_zip_codes(countyZipCodes):
    county_zip_codes = {}
    county_city_zip_codes = {}
    all_zip_codes = []
    try:
        for section in countyZipCodes.find_all('div', class_='naicsSection'):
            county_name = section.text.strip()
            county_zip_codes[county_name] = []
            county_city_zip_codes[county_name] = {}
            for sibling in section.find_next_siblings():
                if 'naicsSection' in sibling.get('class', []):
                    break
                if 'naicsText' in sibling.get('class', []):
                    text = sibling.text.strip()
                    zip_code = text.split()[0]
                    city_name = " ".join(text.split()[1:])
                    if zip_code.isdigit() and len(zip_code) == 5:
                        county_zip_codes[county_name].append(zip_code)
                        if city_name not in county_city_zip_codes[county_name]:
                            county_city_zip_codes[county_name][city_name] = []
                        county_city_zip_codes[county_name][city_name].append(zip_code)
                        all_zip_codes.append(zip_code)
    except Exception as e:
        print(f"Error extracting zip codes: {e}")
        return None, None, None
    return county_zip_codes, county_city_zip_codes, all_zip_codes

def save_data_to_file(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def main():
    zipURL = "https://secure.utah.gov/datarequest/zipcodes.html"
    countyZipCodes = fetch_utah_zip_codes(zipURL)
    if not countyZipCodes:
        print("Failed to fetch or parse the zip codes page.")
        return
    county_zip_codes, county_city_zip_codes, all_zip_codes = extract_zip_codes(countyZipCodes)
    if not county_zip_codes or not county_city_zip_codes or not all_zip_codes:
        print("Failed to extract zip codes.")
        return
    # Save to files
    save_data_to_file(county_zip_codes, 'county_zip_codes.json')
    save_data_to_file(county_city_zip_codes, 'county_city_zip_codes.json')
    save_data_to_file(all_zip_codes, 'all_zip_codes.json')
    print("Data saved to files successfully.")

if __name__ == "__main__":
    main()