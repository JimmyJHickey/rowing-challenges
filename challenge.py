import os
import json
import numpy as np
import pandas as pd
import urllib.request
from datetime import datetime
from shapely.geometry import LineString
from pyproj import Geod

try:
    from shapely.ops import substring
except ImportError:
    def substring(geom, start_dist, end_dist, normalized=False):
        return geom.interpolate(start_dist, normalized=normalized).union(
               geom.interpolate(end_dist, normalized=normalized))


# ---------------------------------------------------------------------------
# One-time download of Leaflet assets so the generated HTML is fully
# self-contained (no CDN calls, no CSP issues on GitHub Pages).
# Files are cached next to this script in _leaflet_cache/ and reused.
# ---------------------------------------------------------------------------

LEAFLET_VERSION = "1.9.4"
_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_leaflet_cache")

_URLS = {
    "css":    f"https://unpkg.com/leaflet@{LEAFLET_VERSION}/dist/leaflet.css",
    "js":     f"https://unpkg.com/leaflet@{LEAFLET_VERSION}/dist/leaflet.js",
    "icon":   f"https://unpkg.com/leaflet@{LEAFLET_VERSION}/dist/images/marker-icon.png",
    "icon2x": f"https://unpkg.com/leaflet@{LEAFLET_VERSION}/dist/images/marker-icon-2x.png",
    "shadow": f"https://unpkg.com/leaflet@{LEAFLET_VERSION}/dist/images/marker-shadow.png",
}


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8")


def _fetch_bytes_b64(url: str) -> str:
    import base64
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    ext  = url.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "gif": "image/gif"}.get(ext, "image/png")
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def _get_leaflet_assets() -> dict:
    """
    Return dict with keys: css, js, icon, icon2x, shadow.
    Downloads from unpkg on first call, then reads from local cache.
    Marker PNGs are stored as base64 data-URIs so no separate files
    are needed at the serving location.
    """
    os.makedirs(_ASSET_DIR, exist_ok=True)

    cache_paths = {
        "css":    os.path.join(_ASSET_DIR, "leaflet.css"),
        "js":     os.path.join(_ASSET_DIR, "leaflet.js"),
        "icon":   os.path.join(_ASSET_DIR, "marker-icon.b64"),
        "icon2x": os.path.join(_ASSET_DIR, "marker-icon-2x.b64"),
        "shadow": os.path.join(_ASSET_DIR, "marker-shadow.b64"),
    }

    assets = {}
    for key, path in cache_paths.items():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                assets[key] = f.read()
        else:
            print(f"[Challenge] Downloading Leaflet asset: {_URLS[key]}")
            if key in ("icon", "icon2x", "shadow"):
                content = _fetch_bytes_b64(_URLS[key])
            else:
                content = _fetch_text(_URLS[key])
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            assets[key] = content

    # Patch the CSS so marker url() references point to our base64 data-URIs
    assets["css"] = (
        assets["css"]
        .replace("images/marker-icon.png",    assets["icon"])
        .replace("images/marker-icon-2x.png", assets["icon2x"])
        .replace("images/marker-shadow.png",  assets["shadow"])
    )

    return assets


# ---------------------------------------------------------------------------
# Challenge class
# ---------------------------------------------------------------------------

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

        self.challenge_name    = challenge_name
        self.start_date        = start_date
        self.flavor_text       = flavor_text
        # plot_file_path should end in .html
        self.plot_file_path    = plot_file_path
        self.full_route_coords = full_route_coords
        self.plot_type         = plot_type

        if self.plot_type not in ["local", "global"]:
            raise ValueError("plot_type must be 'local' or 'global'")

        self.route_length         = self.get_route_length_meters(full_route_coords)
        self.data_csv_path        = data_csv_path
        self.current_meters_rowed = 0

    # ------------------------------------------------------------------ #
    #  Geometry helpers                                                    #
    # ------------------------------------------------------------------ #

    def get_route_length_meters(self, full_route_coords):
        line = LineString(full_route_coords)
        lons, lats = line.xy
        total_length = 0
        geod = Geod(ellps="WGS84")
        for i in range(len(lons) - 1):
            _, _, distance = geod.inv(lons[i], lats[i], lons[i+1], lats[i+1])
            total_length += distance
        return total_length

    # ------------------------------------------------------------------ #
    #  CSV helpers (unchanged)                                             #
    # ------------------------------------------------------------------ #

    def _load_rowing_data(self):
        df = pd.read_csv(self.data_csv_path)
        df.columns = df.columns.str.strip()
        df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
        df.replace("", np.nan, inplace=True)
        df["date"] = pd.to_datetime(df["date"], format="%m/%d/%y")
        df["distance_meters"] = (
            df["distance_meters"].astype(str).str.replace(",", "", regex=False)
        )
        df["distance_meters"] = pd.to_numeric(df["distance_meters"], errors="coerce").fillna(0)
        df["calories"]        = pd.to_numeric(df["calories"],        errors="coerce").fillna(0)
        start = pd.to_datetime(self.start_date)
        return df[df["date"] >= start]

    def _parse_time_to_seconds(self, time_str):
        try:
            parts = time_str.strip().split(":")
            if len(parts) == 3:
                h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
            elif len(parts) == 2:
                h, m, s = 0, int(parts[0]), float(parts[1])
            else:
                return 0.0
            return h * 3600 + m * 60 + s
        except (ValueError, AttributeError):
            return 0.0

    def _seconds_to_hms(self, total_seconds):
        total_seconds = int(total_seconds)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h}h {m:02d}m {s:02d}s"

    # ------------------------------------------------------------------ #
    #  Stats (unchanged)                                                   #
    # ------------------------------------------------------------------ #

    def current_stats(self):
        df = self._load_rowing_data()

        if df.empty:
            return {
                "current_meters_rowed": 0,
                "total_meters_goal":    self.route_length,
                "progress_percent":     0.0,
                "total_time":           "0h 00m 00s",
                "total_calories":       0,
                "player_stats":         {}
            }

        df["total_seconds"] = df["time"].apply(self._parse_time_to_seconds)
        total_meters   = df["distance_meters"].sum()
        total_seconds  = df["total_seconds"].sum()
        total_calories = df["calories"].sum()
        progress = min(total_meters / self.route_length, 1.0)

        player_stats = {}
        for user_name, group in df.groupby("user_name"):
            u_m = group["distance_meters"].sum()
            u_s = group["total_seconds"].sum()
            u_c = group["calories"].sum()
            player_stats[user_name] = {
                "meters_rowed":     int(u_m),
                "time_spent":       self._seconds_to_hms(u_s),
                "calories_burned":  int(u_c),
                "progress_percent": round(min(u_m / self.route_length, 1.0) * 100, 2),
            }

        self.current_meters_rowed = int(total_meters)
        return {
            "current_meters_rowed": self.current_meters_rowed,
            "total_meters_goal":    round(self.route_length, 1),
            "progress_percent":     round(progress * 100, 2),
            "total_time":           self._seconds_to_hms(total_seconds),
            "total_calories":       int(total_calories),
            "player_stats":         player_stats,
        }

    # ------------------------------------------------------------------ #
    #  Progress geometry                                                   #
    # ------------------------------------------------------------------ #

    def _get_progress_coords(self):
        frac = min(
            self.current_meters_rowed / self.route_length if self.route_length > 0 else 0.0,
            1.0
        )
        full_line     = LineString(self.full_route_coords)
        progress_line = substring(full_line, 0, frac, normalized=True)

        if progress_line.geom_type == "LineString":
            prog_coords = list(progress_line.coords)
        else:
            prog_coords = []
            for seg in progress_line.geoms:
                prog_coords.extend(list(seg.coords))

        boat_lon, boat_lat = (prog_coords[-1] if prog_coords else self.full_route_coords[0])
        return self.full_route_coords, prog_coords, boat_lon, boat_lat

    @staticmethod
    def _split_antimeridian(coords_lonlat):
        """
        Split a list of (lon, lat) coords into multiple segments wherever the
        route crosses the antimeridian (±180°).  Returns a list of segments,
        each segment being a list of [lat, lon] pairs ready for Leaflet.

        Strategy: when the longitude jump between two consecutive points is
        greater than 180°, we know the line crossed the antimeridian.  We
        interpolate the crossing latitude and start a new segment, offsetting
        the longitudes so Leaflet never has to draw a line wider than 180°.
        """
        if not coords_lonlat:
            return []

        segments = []
        current  = [[coords_lonlat[0][1], coords_lonlat[0][0]]]  # [lat, lon]

        for i in range(1, len(coords_lonlat)):
            lon0, lat0 = coords_lonlat[i - 1]
            lon1, lat1 = coords_lonlat[i]
            dlon = lon1 - lon0

            if abs(dlon) > 180:
                # Interpolate crossing latitude
                # Normalise so dlon is the "short way" around
                if dlon > 0:
                    lon1_adj = lon1 - 360
                else:
                    lon1_adj = lon1 + 360

                # Fraction of the segment at which we hit ±180
                if lon0 != lon1_adj:
                    t = (180 * (1 if dlon < 0 else -1) - lon0) / (lon1_adj - lon0)
                else:
                    t = 0.5
                t = max(0.0, min(1.0, t))
                cross_lat = lat0 + t * (lat1 - lat0)
                cross_lon = 180 if dlon < 0 else -180

                current.append([cross_lat, cross_lon])
                segments.append(current)

                # Start the new segment on the other side
                current = [[cross_lat, -cross_lon], [lat1, lon1]]
            else:
                current.append([lat1, lon1])

        if current:
            segments.append(current)

        return segments

    # ------------------------------------------------------------------ #
    #  Leaflet HTML generation — fully self-contained                     #
    # ------------------------------------------------------------------ #

    def generate_leaflet_map(self):
        """
        Write a fully self-contained HTML file with Leaflet CSS + JS inlined.
        Routes that cross the antimeridian (±180°) are pre-split in Python
        so Leaflet never draws a line across the globe.
        Leaflet assets are downloaded once and cached in _leaflet_cache/.
        """
        stats = self.current_stats()   # populates current_meters_rowed
        full_coords, prog_coords, boat_lon, boat_lat = self._get_progress_coords()

        # Split at the antimeridian — returns lists of [[lat,lon], ...] segments
        full_segs = self._split_antimeridian(full_coords)
        prog_segs = self._split_antimeridian(prog_coords)

        # Flat [lat,lon] list used only for fitBounds / start+finish markers
        full_ll = [[lat, lon] for lon, lat in full_coords]
        mid     = full_ll[len(full_ll) // 2] if full_ll else [0, 0]
        zoom    = 5 if self.plot_type == "local" else 2
        pct     = stats["progress_percent"]

        assets = _get_leaflet_assets()

        popup_html = (
            f"<b>Current Position</b><br/>"
            f"{stats['current_meters_rowed']:,}&nbsp;m rowed<br/>"
            f"{pct}% complete<br/>"
            f"Time: {stats['total_time']}<br/>"
            f"Calories: {stats['total_calories']:,}"
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{self.challenge_name}</title>
  <style>
{assets['css']}
  </style>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body, #map {{ width: 100%; height: 100%; }}
  </style>
</head>
<body>
  <div id="map"></div>

  <script>
{assets['js']}
  </script>
  <script>
    const fullSegs = {json.dumps(full_segs)};
    const progSegs = {json.dumps(prog_segs)};
    const fullFlat = {json.dumps(full_ll)};
    const boatLatLng = [{boat_lat}, {boat_lon}];

    const map = L.map('map');

    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }}).addTo(map);

    // Full route ghost
    fullSegs.forEach((seg, i) => {{
      if (seg.length > 1) {{
        L.polyline(seg, {{
          color: '#888', weight: 3, dashArray: '8 6', opacity: 0.5,
        }}).addTo(map).bindTooltip(i === 0 ? 'Full route' : '');
      }}
    }});

    // Progress line
    progSegs.forEach((seg, i) => {{
      if (seg.length > 1) {{
        L.polyline(seg, {{
          color: '#0047AB', weight: 5, opacity: 0.9,
        }}).addTo(map).bindTooltip(i === 0 ? 'Distance rowed so far' : '');
      }}
    }});

    // Rowing emoji marker
    const rowerIcon = L.divIcon({{
      html: '<span style="font-size:24px;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,.5));">🚣</span>',
      iconSize: [28, 28], iconAnchor: [14, 14], className: '',
    }});

    L.marker(boatLatLng, {{ icon: rowerIcon }})
      .addTo(map)
      .bindPopup(`{popup_html}`)
      .openPopup();

    // Start & finish markers
    if (fullFlat.length > 0) {{
      L.circleMarker(fullFlat[0], {{
        radius: 7, color: '#2a9d8f', fillColor: '#2a9d8f', fillOpacity: 1,
      }}).addTo(map).bindTooltip('Start');

      L.circleMarker(fullFlat[fullFlat.length - 1], {{
        radius: 7, color: '#e76f51', fillColor: '#e76f51', fillOpacity: 1,
      }}).addTo(map).bindTooltip('Finish');
    }}

    // Auto-fit — use the flat list so bounds are calculated correctly
    if (fullFlat.length > 1) {{
      map.fitBounds(L.polyline(fullFlat).getBounds(), {{ padding: [40, 40] }});
    }} else {{
      map.setView({mid}, {zoom});
    }}
  </script>
</body>
</html>
"""
        os.makedirs(os.path.dirname(os.path.abspath(self.plot_file_path)), exist_ok=True)
        with open(self.plot_file_path, "w", encoding="utf-8") as f:
            f.write(html)

    # Backwards-compat wrappers so existing call-sites don't break
    def generate_local_plot(self):
        self.generate_leaflet_map()

    def generate_global_plot(self):
        self.generate_leaflet_map()

    # ------------------------------------------------------------------ #
    #  Markdown output                                                     #
    # ------------------------------------------------------------------ #

    def to_markdown(self):
        stats = self.current_stats()
        self.generate_leaflet_map()

        plot_rel_path = self.plot_file_path.split('jimmyjhickey.com/')[1]

        lines = [
            f"## {self.challenge_name}",
            "",
            f"{self.flavor_text}",
            "",
            f'<iframe src="{plot_rel_path}" '
            f'style="display:block; width:100%; max-width:800px; height:520px; '
            f'border:none; border-radius:10px; margin:20px auto;" '
            f'loading="lazy" title="{self.challenge_name} map"></iframe>',
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

        player_stats_sorted = dict(
            sorted(stats["player_stats"].items(),
                   key=lambda x: x[1]["meters_rowed"], reverse=True)
        )

        for user_name, p in player_stats_sorted.items():
            lines.append(
                f"| {user_name} "
                f"| {p['meters_rowed']:,} "
                f"| {p['progress_percent']}% "
                f"| {p['time_spent']} "
                f"| {p['calories_burned']:,} |"
            )

        return "\n".join(lines)