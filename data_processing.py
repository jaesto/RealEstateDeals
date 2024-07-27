import pandas as pd
import traceback
import csv

def capitalize_names(name):
    return ' '.join(word.capitalize() if word else '' for word in name.split())

def get_unique_utah_agents(astro_agents, scrapped_agents):
    merged_agents = scrapped_agents.merge(astro_agents, on=['First Name', 'Last Name'], how='left', indicator=True)
    unique_agents = merged_agents[merged_agents['_merge'] == 'left_only'].drop(columns=['_merge', 'Phone_y']).rename(columns={'Phone_x': 'Phone'})
    grouped_agents = unique_agents.groupby(['First Name', 'Last Name', 'Phone'], as_index=False).agg({'City': lambda x: ', '.join(set(x))})
    return grouped_agents

def update_city_tags(filename='unique_utah_agents.csv', output_filename='unique_utah_agents_updated.csv'):
    try:
        # Load unique agents from CSV
        unique_agents = pd.read_csv(filename)

        # Capitalize names
        unique_agents['First Name'] = unique_agents['First Name'].apply(capitalize_names)
        unique_agents['Last Name'] = unique_agents['Last Name'].apply(capitalize_names)

        # Ensure the 'City' column is treated as a string
        unique_agents['City'] = unique_agents['City'].astype(str)

        # Update city tags
        unique_agents['City'] = unique_agents['City'].apply(lambda cities: ', '.join([f"{city.strip()} Utah Market" for city in cities.split(',') if isinstance(city, str)]))

        # Add "realtor" tag
        unique_agents['Tags'] = unique_agents['City'] + ', realtor'

        # Drop the 'City' column
        unique_agents = unique_agents.drop(columns=['City'])

        # Save the updated CSV without quotes and escape characters
        unique_agents.to_csv(output_filename, index=False, quoting=csv.QUOTE_MINIMAL)
        print(f"Updated unique Utah agents saved to '{output_filename}'.")
    except Exception as e:
        print(f"Error updating city tags: {e}")
        print(traceback.format_exc())
