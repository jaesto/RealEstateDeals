import time
import datetime

class Listing:
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
        self.agent_first_name = ''
        self.agent_last_name = ''
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
        self.email = ''
        self.price_change_date = ''  # New attribute to track price change date
        self.price_change_percentage = 0.0  # New attribute to track price change percentage
        self.type = '' # New field for property type
        self.style = '' # New field for property style
        self.days_on_ure = ''  # New field for days on URE


    def __repr__(self):
        return (f"Listing(mls={self.mls}, price={self.price}, address={self.address}, city={self.city}, "
                f"state={self.state}, zip={self.zip}, agent_name={self.agent_name}, agent_phone={self.agent_phone}, "
                f"broker_name={self.broker_name}, broker_phone={self.broker_phone})")
    
    @classmethod
    def from_dict(cls, data):
        listing = cls()
        listing.__dict__.update(data)
        return listing
