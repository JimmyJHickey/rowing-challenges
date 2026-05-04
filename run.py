import os
import sys
import builtins

# This manually injects 'os' into the global namespace so that 
# even if a broken library forgets to import it, it's already there.
builtins.os = os

import matplotlib
matplotlib.use('Agg')  # This tells Matplotlib to run without a GUI
import os
from profile_scraper import ProfileScraper
import json
from challenge import Challenge


json_path = "/home/pi/git/rowing-challenges/users.json"
with open(json_path, 'r') as file:
    users_data = json.load(file)
for user in users_data:

    my_scraper = ProfileScraper(
        profile_url = user["profile_url"],
        user_name = user["user_name"], 
        csv_path = "/home/pi/git/rowing-challenges/concept2_workouts.csv"
    )
    my_scraper.run()

north_channel_coords = [
    (-5.885, 54.646),  # Start: Donaghadee Harbour, NI
    (-5.800, 54.660),  # Exiting the coast into the main channel
    (-5.700, 54.700),  # Mid-channel (The "Deep" water)
    (-5.550, 54.750),  # Approaching the peak of the tidal curve
    (-5.400, 54.800),  # Pushed North/East by the flood tide
    (-5.200, 54.840),  # Turning toward the Scottish coastline
    (-5.150, 54.855),  # Near Killantringan Lighthouse
    (-5.120, 54.843),  # Approaching Portpatrick cliffs
    (-5.118, 54.842)   # Finish: Portpatrick, Scotland
]

north_channel_name = "Rowing the North Channel"
north_channel_flavor = "Also known as the Sruth na Maoile or the Sheuch."
north_channel_challenge = Challenge(
    challenge_name=north_channel_name,
    start_date="2026-05-04",
    full_route_coords = north_channel_coords,
    plot_type="local",
    flavor_text = north_channel_flavor,
    plot_file_path=f"/home/pi/git/jimmyjhickey.com/img/rowing/{north_channel_name.replace(' ', '_')}.png",
    data_csv_path="/home/pi/git/rowing-challenges/concept2_workouts.csv"
)



magellan_coords = [
    (-6.35, 36.78),    # Sanlúcar de Barrameda, Spain (Departure)
    (-14.00, 32.00),   # Atlantic Buffer (Avoiding the Moroccan coast)
    (-15.41, 28.11),   # Canary Islands
    (-25.00, 15.00),   # Cape Verde (Wide berth to catch trade winds)
    (-10.00, 0.00),    # Equatorial Crossing (Standard naval path toward Brazil)
    (-43.20, -22.90),  # Rio de Janeiro, Brazil
    (-56.16, -34.90),  # Río de la Plata (Exploring for the passage)
    (-67.70, -49.30),  # Puerto San Julián (The "Winter" stop)
    (-68.20, -52.40),  # Entrance to the Strait
    (-71.00, -53.50),  # Deep in the Strait of Magellan
    (-75.00, -52.50),  # Exit into the Pacific (Mar del Sur)
    (-100.0, -30.0),   # South Pacific "S" curve
    (-140.0, -15.0),   # Approaching the Equator
    (144.75, 13.44),   # Guam (Arrival in Marianas)
    (125.60, 11.00),   # Homonhon Island (First landing in Philippines)
    (123.90, 10.31),   # Cebu (Magellan’s death site)
    (121.00, 7.00),    # Sulu Sea (Navigating toward the Moluccas)
    (127.39, 0.64),    # Tidore, Moluccas (The Spice Islands)
    (115.00, -15.00),  # Exiting the Indonesian Archipelago
    (80.00, -30.00),   # Central Indian Ocean
    (18.42, -34.35),   # Cape of Good Hope, South Africa
    (5.00, -10.00),    # Atlantic Buffer (Avoiding the Gulf of Guinea)
    (-20.00, 15.00),   # Passing West of Cape Verde (Heading North)
    (-18.00, 28.00),   # Canary Islands (Homeward bound)
    (-9.00, 37.00),    # Passing Cape St. Vincent, Portugal
    (-6.35, 36.78)     # Sanlúcar de Barrameda, Spain (Arrival)
]

magellan_challenge_name = "Circumnavigating the Globe like Magellan"
magellan_challenge = Challenge(
    challenge_name=magellan_challenge_name,
    start_date="2026-04-17",
    full_route_coords = magellan_coords,
    plot_type="global",
    flavor_text = "Will we mutiny as well?",
    plot_file_path=f"/home/pi/git/jimmyjhickey.com/img/rowing/{magellan_challenge_name.replace(' ', '_')}.png",
    data_csv_path="/home/pi/git/rowing-challenges/concept2_workouts.csv"
)


out_file = "/home/pi/git/jimmyjhickey.com/rowing.md"
with open('/home/pi/git/rowing-challenges/webpage_format.txt', 'r') as file:
    template_content = file.read()
            
    final_webpage = template_content.format(
            challenge_1 = north_channel_challenge.to_markdown(),
        challenge_2 = magellan_challenge.to_markdown()
    )
    
    with open(out_file, 'w') as output_file:
        output_file.write(final_webpage)
