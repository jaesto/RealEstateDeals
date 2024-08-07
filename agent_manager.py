# agent_manager.py
import pandas as pd
from data_loader import load_astro_agents, normalize_phone_number
from data_processing import get_unique_utah_agents, update_city_tags

class AgentManager:
    def __init__(self, contacts_file):
        self.contacts_file = contacts_file

    def update_agents(self, current_listings):
        """
        Updates agent data based on current listings.

        Args:
            current_listings (dict): A dictionary of current listings.
        """
        # Load astro agents
        astro_agents = load_astro_agents(self.contacts_file)
        if astro_agents.empty:
            print("No astro agents loaded. Exiting.")
            return

        # Get scrapped agents
        scrapped_agents = self.get_scrapped_agents(current_listings)

        # Ensure the columns are strings
        scrapped_agents['First Name'] = scrapped_agents['First Name'].astype(str)
        scrapped_agents['Last Name'] = scrapped_agents['Last Name'].astype(str)

        # Get unique Utah agents
        unique_utah_agents = get_unique_utah_agents(astro_agents, scrapped_agents)

        # Save unique Utah agents to a CSV file
        unique_utah_agents.to_csv('unique_utah_agents.csv', index=False)
        print("Unique Utah agents saved to 'unique_utah_agents.csv'.")

        # Update city tags
        update_city_tags('unique_utah_agents.csv', 'unique_utah_agents_updated.csv')

    def get_scrapped_agents(self, current_listings):
        """
        Extracts scrapped agent data from current listings.

        Args:
            current_listings (dict): A dictionary of current listings.

        Returns:
            DataFrame: A DataFrame containing agent data.
        """
        return pd.DataFrame([{
            'First Name': listing.agent_first_name,
            'Last Name': listing.agent_last_name,
            'Phone': normalize_phone_number(listing.agent_phone),
            'City': listing.city
        } for listing in current_listings.values() if listing.agent_phone])
