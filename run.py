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

git_dir = "/home/jimmy/"
json_path = f"{git_dir}rowing-challenges/users.json"
with open(json_path, 'r') as file:
    users_data = json.load(file)
for user in users_data:

    my_scraper = ProfileScraper(
        profile_url = user["profile_url"],
        user_name = user["user_name"], 
        csv_path = f"{git_dir}/rowing-challenges/concept2_workouts.csv"
    )
    my_scraper.run()

cook_strait_challenge_name = "Rowing the Cook Strait"
cook_strait_coords = [
(174.365, -41.199), # Start: Shore of Perano Head (Arapaoa Island)
    (174.490, -41.240), # Mid-Strait: Staying in the deep channel
    (174.615, -41.278)  # End: Shore of Cape Terawhiti (North Island)
]
cook_strait_challenge = Challenge(
    challenge_name=cook_strait_challenge_name,
    start_date="2026-05-12",
    full_route_coords = cook_strait_coords,
    plot_type="local",
    flavor_text = "Also known as Te Moana-o-Raukawa, which is probably better than naming it after a colonizer.",
    plot_file_path=f"../jimmyjhickey.com/img/rowing/{cook_strait_challenge_name.replace(' ', '_')}.html",
    data_csv_path="concept2_workouts.csv"
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
    plot_file_path=f"{git_dir}jimmyjhickey.com/img/rowing/{magellan_challenge_name.replace(' ', '_')}.html",
    data_csv_path=f"{git_dir}rowing-challenges/concept2_workouts.csv"
)


out_file = f"{git_dir}jimmyjhickey.com/rowing.md"
with open(f'{git_dir}rowing-challenges/webpage_format.txt', 'r') as file:
    template_content = file.read()
            
    final_webpage = template_content.format(
        challenge_1 = cook_strait_challenge.to_markdown(),
        challenge_2 = magellan_challenge.to_markdown()
    )
    
    with open(out_file, 'w') as output_file:
        output_file.write(final_webpage)
