from neo4j import GraphDatabase
import json

class DatabaseOps:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def send_to_neo4j(self, listing, status, additionalText, listing_type):
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
                    l.propertyDetails = $property_details,
                    l.price_change_date = $price_change_date,
                    l.price_change_percentage = $price_change_percentage
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
                            description=listing.description, property_details=json.dumps(listing.property_details),
                            price_change_date=listing.price_change_date,
                            price_change_percentage=listing.price_change_percentage)

                # Create or update the agent node
                agent_query = """
                MERGE (a:Agent {name: $agent_name, phone: $agent_phone})
                """
                session.run(agent_query, agent_name=listing.agent_name, agent_phone=listing.agent_phone)

                # Create or update the broker node
                broker_query = """
                MERGE (b:Broker {name: $broker_name, phone: $broker_phone})
                """
                session.run(broker_query, broker_name=listing.broker_name, broker_phone=listing.broker_phone)

                # Create the relationships between the listing and the agent, and between the listing and the broker
                agent_listing_relationship_query = f"""
                MATCH (a:Agent {{name: $agent_name, phone: $agent_phone}}), (l:{listing_type} {{mls: $mls}})
                MERGE (a)-[:AGENT_OF]->(l)
                """
                session.run(agent_listing_relationship_query, agent_name=listing.agent_name, agent_phone=listing.agent_phone, mls=listing.mls)

                broker_listing_relationship_query = f"""
                MATCH (b:Broker {{name: $broker_name, phone: $broker_phone}}), (l:{listing_type} {{mls: $mls}})
                MERGE (b)-[:BROKERED_BY]->(l)
                """
                session.run(broker_listing_relationship_query, broker_name=listing.broker_name, broker_phone=listing.broker_phone, mls=listing.mls)

                # Create the relationship between the agent and the broker
                agent_broker_relationship_query = """
                MATCH (a:Agent {name: $agent_name, phone: $agent_phone}), (b:Broker {name: $broker_name, phone: $broker_phone})
                MERGE (a)-[:WORKS_FOR]->(b)
                """
                session.run(agent_broker_relationship_query, agent_name=listing.agent_name, agent_phone=listing.agent_phone, broker_name=listing.broker_name, broker_phone=listing.broker_phone)
        except Exception as e:
            print(f"Error sending data to Neo4j: {e}")

