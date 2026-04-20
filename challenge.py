import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx
from shapely.geometry import LineString
from shapely.ops import substring
import pandas as pd
from datetime import datetime
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import LineString
from pyproj import Geod
from shapely.ops import substring


class Challenge():
    def __init__(self,
                 challenge_name,
                 start_date,                
                 full_route_coords,
                 plot_type,
                 flavor_text,
                 plot_file_path,
                 data_csv_path
                 ):
        
        self.challenge_name = challenge_name
        self.start_date = start_date
        self.flavor_text = flavor_text
        self.plot_file_path = plot_file_path
        self.full_route_coords = full_route_coords
        self.plot_type = plot_type

        if self.plot_type not in ["local", "global"]:
            raise ValueError("plot_type must be 'local' or 'global'")
        
        self.route_length = self.get_route_length_meters(full_route_coords)
        self.data_csv_path = data_csv_path
        self.current_meters_rowed = 0

    def get_route_length_meters(self, coords):
        # The WGS84 ellipsoid is the global standard (used by GPS)
        geod = Geod(ellps="WGS84")
        line = LineString(coords)
        
        # This calculates the length along the curve of the Earth
        return geod.geometry_length(line)

    def _load_rowing_data(self):
        """
        Read the CSV and return only rows on or after start_date,
        with numeric columns cast to the correct types.
        """
        df = pd.read_csv(self.data_csv_path)

        # Strip whitespace from column names in case of encoding issues
        df.columns = df.columns.str.strip()

        # Strip whitespace from all string columns
        df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

        # Replace empty strings with NaN before numeric conversion
        df.replace("", pd.NA, inplace=True)

        # Parse dates
        df["date"] = pd.to_datetime(df["date"], format="%m/%d/%y")
        
        # Strip commas from distance in case any slipped through (e.g. "12,995")
        df["distance_meters"] = df["distance_meters"].astype(str).str.replace(",", "", regex=False)
        df["distance_meters"] = pd.to_numeric(df["distance_meters"], errors="coerce").fillna(0)
        df["calories"] = pd.to_numeric(df["calories"], errors="coerce").fillna(0)

        # Filter to only rows on or after the challenge start date
        start = pd.to_datetime(self.start_date)
        df = df[df["date"] >= start]

        return df


    def _parse_time_to_seconds(self, time_str):
        """
        Convert a time string in HH:MM:SS.S or MM:SS.S format to total seconds.
        e.g. "1:00:00.0" -> 3600.0,  "10:00.0" -> 600.0
        """
        try:
            parts = time_str.strip().split(":")
            if len(parts) == 3:
                hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
            elif len(parts) == 2:
                hours, minutes, seconds = 0, int(parts[0]), float(parts[1])
            else:
                return 0.0
            return hours * 3600 + minutes * 60 + seconds
        except (ValueError, AttributeError):
            return 0.0


    def _seconds_to_hms(self, total_seconds):
        """Format a number of seconds as a readable HH:MM:SS string."""
        total_seconds = int(total_seconds)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h}h {m:02d}m {s:02d}s"


    def current_stats(self):
        df = self._load_rowing_data()

        if df.empty:
            return {
                "current_meters_rowed": 0,
                "total_meters_goal": self.route_length,
                "progress_percent": 0.0,
                "total_time": "0h 00m 00s",
                "total_calories": 0,
                "player_stats": {}
            }

        # --- Total seconds per row ---
        df["total_seconds"] = df["time"].apply(self._parse_time_to_seconds)

        # --- Overall totals ---
        total_meters = df["distance_meters"].sum()
        total_seconds = df["total_seconds"].sum()
        total_calories = df["calories"].sum()
        progress = min(total_meters / self.route_length, 1.0)  # cap at 100%

        # --- Per-user stats ---
        player_stats = {}
        for user_name, group in df.groupby("user_name"):
            user_meters = group["distance_meters"].sum()
            user_seconds = group["total_seconds"].sum()
            user_calories = group["calories"].sum()
            user_progress = min(user_meters / self.route_length, 1.0)

            player_stats[user_name] = {
                "meters_rowed":      int(user_meters),
                "time_spent":        self._seconds_to_hms(user_seconds),
                "calories_burned":   int(user_calories),
                "progress_percent":  round(user_progress * 100, 2),
            }

        self.current_meters_rowed = int(total_meters)  # Store for plotting
        return {
            "current_meters_rowed": self.current_meters_rowed,
            "total_meters_goal":    round(self.route_length, 1),
            "progress_percent":     round(progress * 100, 2),
            "total_time":           self._seconds_to_hms(total_seconds),
            "total_calories":       int(total_calories),
            "player_stats":         player_stats,
        }
    

    def generate_local_plot(self):
        # 1. SETUP DATA
        # Example coordinates for a Dover -> Calais crossing
        total_meters_goal = self.get_route_length_meters(self.full_route_coords)
        progress_percent = self.current_meters_rowed / total_meters_goal

        # 2. CREATE GEOMETRY
        full_line = LineString(self.full_route_coords)
        # The "Fix": Accuracy-based splitting
        progress_line = substring(full_line, 0, progress_percent, normalized=True)

        # 3. CONVERT TO MAP PROJECTION (Crucial Step)
        # We create a GeoSeries in Lat/Lon (4326) and convert to Web Mercator (3857)
        gs_full = gpd.GeoSeries([full_line], crs="EPSG:4326").to_crs(epsg=3857)
        gs_prog = gpd.GeoSeries([progress_line], crs="EPSG:4326").to_crs(epsg=3857)

        
        # 4. PLOTTING
        # Use constrained_layout=True to help manage the space automatically
        fig, ax = plt.subplots(figsize=(12, 8), constrained_layout=True)

        # Plot the lines
        gs_full.plot(ax=ax, color='black', linewidth=3, linestyle='--', alpha=0.3, label='Full Route')
        gs_prog.plot(ax=ax, color='#0047AB', linewidth=5, label='Current Progress')

        # Plot the "Boat"
        boat_coords = gs_prog.geometry.iloc[0].coords[-1]
        ax.scatter(boat_coords[0], boat_coords[1], color='red', s=100, zorder=5, label='Current Position')

       
        # 5. ADD THE BACKGROUND MAP
        ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

        # THE FIXES FOR THE BORDER:
        ax.set_axis_off()
        
        # 1. Remove internal margins from the axes
        ax.margins(0)
        ax.xaxis.set_major_locator(plt.NullLocator())
        ax.yaxis.set_major_locator(plt.NullLocator())

        # 2. Add legend (Note: If the legend is outside the map, 
        # it will force a border. Keeping it 'upper right' inside is fine.)
        plt.legend(loc='upper right')

        # 3. Save with zero padding and tight bounding box
        plt.savefig(
            self.plot_file_path, 
            dpi=300, 
            bbox_inches='tight', # Removes the excess whitespace
            pad_inches=0         # Sets that whitespace to zero
        )
        plt.close(fig) # Good practice to close the figure to free memory


    def generate_global_plot(self):
        # 1. SETUP DATA
        # Magellan route coordinates (Long, Lat)
        coords = self.full_route_coords
        total_meters_goal = self.get_route_length_meters(coords)
        progress_percent = self.current_meters_rowed / total_meters_goal

        # 2. CREATE GEOMETRY
        full_line = LineString(coords)
        # Using the accuracy fix from before
        progress_line = substring(full_line, 0, progress_percent, normalized=True)

        # 3. PLOTTING WITH CARTOPY
        # We use Robinson projection for a nice "world map" look
        fig = plt.figure(figsize=(15, 10))
        ax = plt.axes(projection=ccrs.Robinson(central_longitude=0))

        # Add map features so it looks like a real map
        ax.add_feature(cfeature.LAND, facecolor='#f9f9f9')
        ax.add_feature(cfeature.OCEAN, facecolor='#e0f3ff')
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linestyle=':', alpha=0.5)

        # 4. THE MAGIC LINE FIX
        # transform=ccrs.Geodetic() tells Cartopy these are Lat/Lon points 
        # and to wrap them around the globe rather than cutting across.
        
        # Plot Full Route (Ghost)
        ax.plot([c[0] for c in coords], [c[1] for c in coords],
                color='gray', linestyle='--', linewidth=1.5, alpha=0.5,
                transform=ccrs.Geodetic(), label='Full Expedition')

        # Plot Progress
        prog_x, prog_y = progress_line.xy
        ax.plot(prog_x, prog_y,
                color='#0047AB', linewidth=4,
                transform=ccrs.Geodetic(), label='Our Progress')

        # Plot Current Position
        boat_lon, boat_lat = progress_line.coords[-1]
        ax.plot(boat_lon, boat_lat, 'ro', markersize=8, 
                transform=ccrs.Geodetic(), zorder=5)

        # 5. REMOVE BORDERS & SAVE
        ax.set_global() # Ensures the whole world is shown
        plt.legend(loc='lower left')
        
        # Final cleanup to remove white space
        plt.savefig(self.plot_file_path, 
                    dpi=300, 
                    bbox_inches='tight', 
                    pad_inches=0,
                    transparent=True)
        plt.close(fig)


    def to_markdown(self):
        """Generate a formatted Markdown summary of the current challenge stats."""
        stats = self.current_stats()

        # Ensure the plot is up to date with current stats
        if self.plot_type == "global":
            self.generate_global_plot()
        elif self.plot_type == "local":
            self.generate_local_plot()

        # path that will be used by the web page to find the images
        plot_file_path_local = self.plot_file_path.split('jimmyjhickey.com/')[1]

        lines = [
            f"## {self.challenge_name}",
            "",
            f"{self.flavor_text}",
            "",
            # f"![Route Map]({self.plot_file_path})",
f'<img src="{plot_file_path_local}" style="display: block; width: 80%; max-width: 800px; margin: 20px auto; height: auto;" />'            
            "",
            f"**Dates:** {self.start_date} -- Present",
            "",
            f"**Meters rowed:** {stats['current_meters_rowed']:,}",
            "",
            f"**Total meters:** {stats['total_meters_goal']:,.1f}",
            "",
            f"**Completion Percentage:** {stats['progress_percent']}%",
            "",
            "| Name | Meters Rowed | % of Total | Time Rowed | Calories Burned |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for user_name, p in stats["player_stats"].items():
            lines.append(
                f"| {user_name} "
                f"| {p['meters_rowed']:,} "
                f"| {p['progress_percent']}% "
                f"| {p['time_spent']} "
                f"| {p['calories_burned']:,} |"
            )
        
        return "\n".join(lines)
