"""
Concept2 Logbook Scraper
Detects new RowErg workout entries and stores distance, time, and calories
from each workout's detail page into a CSV file.
Intended to be run on a schedule via cron job.
"""

import csv
import logging
import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import re

class ProfileScraper():
    def __init__(self, profile_url: str, user_name: str, csv_path: str):
        self.profile_url = profile_url
        self.user_name = user_name
        self.csv_path = csv_path
        
        self.csv_fields = [
            "user_name", "workout_id", "workout_url", "date", "workout_desc",
            "distance_meters", "time", "calories", "scraped_at"
        ]

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("scraper.log"),
            ],
        )
        self.log = logging.getLogger(__name__)

    # ---------------------------------------------------------------------------
    # CSV helpers
    # ---------------------------------------------------------------------------

    def load_known_ids(self, csv_path: str) -> set:
        """Return the set of workout_ids already saved in the CSV."""
        if not os.path.exists(csv_path):
            return set()
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return {row["workout_id"] for row in reader}


    def append_workouts(self, csv_path: str, workouts: list[dict]) -> None:
        """Append new workout rows to the CSV, creating it with a header if needed."""
        write_header = not os.path.exists(csv_path)
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_fields)
            if write_header:
                writer.writeheader()
            writer.writerows(workouts)


    # ---------------------------------------------------------------------------
    # Scraping helpers
    # ---------------------------------------------------------------------------

    def fetch_html(self, url: str) -> str:
        response = requests.get(url,
                                #  headers=self.headers,
                                 timeout=15)
        response.raise_for_status()
        return response.text


    def parse_log_page(self, html: str) -> list[dict]:
        """Parse the logbook index page into a list of workout dicts."""
        soup = BeautifulSoup(html, "html.parser")
        entries = []

        # Find the workouts table by its known self.headers
        workout_table = None
        for table in soup.find_all("table"):
            self.headers = [th.get_text(strip=True) for th in table.find_all("th")]
            if "Date" in self.headers and "Workout" in self.headers and "Score" in self.headers:
                workout_table = table
                break

        if not workout_table:
            self.log.warning("Could not find the workouts table.")
            return entries

        for row in workout_table.find_all("tr")[1:]:  # skip header row
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            link_tag = row.find("a", href=lambda h: h and "/log/" in h)
            if not link_tag:
                continue

            workout_url = link_tag["href"]
            workout_id = workout_url.rstrip("/").split("/")[-1]
            machine_type = cells[4].get_text(strip=True)

            entries.append({
                "user_name":      self.user_name,
                "workout_id":   workout_id,
                "workout_url":  workout_url,
                "date":         cells[0].get_text(strip=True),
                "workout_desc": cells[1].get_text(strip=True),
                "machine_type": machine_type,
            })

        return entries


    def scrape_rowerg_detail(self, workout_url: str) -> dict | None:
        """
        Scrape distance (meters), time, and calories from a RowErg workout page.
        Returns a dict with keys: distance_meters, time, calories.
        Returns None if the data cannot be found.
        """
        html = self.fetch_html(workout_url)
        time.sleep(0.5)  # be polite to the server
        soup = BeautifulSoup(html, "html.parser")

        stats_container = soup.find('div', class_='workout__stats')

        # Define a helper to search inside the container we just found
        def extract_val(label):
            label_p = stats_container.find('p', string=label)
            if label_p:
                return label_p.find_previous_sibling('span').get_text(strip=True)
            # return None

        # 3. Extract and Clean

        cal_str = extract_val("Calories")
        distance_str = re.sub(r"[,]", "", extract_val("Meters"))
        time_str     = extract_val("Time")

        # Formatting values
        calories = int(cal_str) if cal_str else 0

        # --- Overall Distance and Overall Time by finding their <th> tags ---
        overall_distance = None
        overall_time = None

        for th in soup.find_all("th"):
            if th.get_text(strip=True) == "Overall Distance":
                td = th.find_next_sibling("td")
                if td:
                    overall_distance = td.get_text(strip=True)
            elif th.get_text(strip=True) == "Overall Time":
                td = th.find_next_sibling("td")
                if td:
                    overall_time = td.get_text(strip=True)

        overall_time = overall_time if overall_time else time_str
        overall_distance = overall_distance if overall_distance else distance_str

        if not all([overall_distance, overall_time, calories]):
            self.log.warning(
                "Could not find all stats on page: %s — "
                "overall_distance=%s, overall_time=%s, calories=%s",
                workout_url, overall_distance, overall_time, calories
            )
            return None

        distance_meters = re.sub(r",", "", overall_distance)

        return {
            "distance_meters": distance_meters,
            "time":            overall_time,
            "calories":        calories,
        }


    # ---------------------------------------------------------------------------
    # Run routine
    # ---------------------------------------------------------------------------

    def run(self) -> None:
        self.log.info("Starting Concept2 logbook check …")

        known_ids = self.load_known_ids(self.csv_path)
        self.log.info("Known workout IDs in CSV: %d", len(known_ids))

        try:
            html = self.fetch_html(self.profile_url)
            entries = self.parse_log_page(html)
        except requests.HTTPError as exc:
            self.log.error("HTTP error fetching logbook: %s", exc)
            return
        except Exception as exc:
            self.log.exception("Unexpected error fetching logbook: %s", exc)
            return

        if not entries:
            self.log.warning("No entries parsed — page structure may have changed.")
            return

        new_workouts = []
        for entry in entries:
            if entry["workout_id"] in known_ids:
                continue

            if entry["machine_type"] != "RowErg":
                self.log.info("Skipping non-RowErg workout: %s (%s)", entry["workout_id"], entry["machine_type"])
                continue

            self.log.info("New RowErg entry: %s on %s", entry["workout_id"], entry["date"])

            try:
                detail = self.scrape_rowerg_detail(entry["workout_url"])
            except Exception as exc:
                self.log.warning("Could not scrape detail page %s: %s", entry["workout_url"], exc)
                detail = None

            new_workouts.append({
                "user_name":         entry["user_name"],
                "workout_id":      entry["workout_id"],
                "workout_url":     entry["workout_url"],
                "date":            entry["date"],
                "workout_desc":    entry["workout_desc"],
                "distance_meters": detail["distance_meters"] if detail else "",
                "time":            detail["time"]            if detail else "",
                "calories":        detail["calories"]        if detail else "",
                "scraped_at":      datetime.utcnow().isoformat(),
            })

            time.sleep(1)  # be polite to the server

        if new_workouts:
            self.append_workouts(self.csv_path, new_workouts)
            self.log.info("Saved %d new RowErg workout(s) to %s", len(new_workouts), self.csv_path)
        else:
            self.log.info("No new RowErg workouts found.")
        return len(new_workouts) > 0
