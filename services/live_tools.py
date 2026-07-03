import urllib.request
import urllib.parse
import json
import webbrowser
from typing import Optional


class LiveTools:

    # ================================================================
    # WEATHER FETCHER
    # ================================================================
    @staticmethod
    def get_current_weather(location: str = "Delhi") -> str:
        """
        Fetches live weather data from wttr.in JSON endpoint.
        Includes:
        - HTTP status validation
        - JSON validation
        - Graceful error messages
        - Safe field extraction
        """
        try:
            location = (location or "").strip()
            if not location:
                location = "Delhi"

            loc_clean = urllib.parse.quote(location)
            url = f"https://wttr.in/{loc_clean}?format=j1"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (DiabloDesktopAssistant)"}
            )

            with urllib.request.urlopen(req, timeout=6.0) as response:
                # Validate HTTP status
                if response.status != 200:
                    return f"Weather service returned HTTP {response.status}. Please try again."

                # Validate content type
                content_type = response.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    return "Weather service returned unexpected response format (non-JSON)."

                raw_data = response.read().decode("utf-8")

            # Parse JSON safely
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                return "Weather service returned malformed JSON data."

            current_conditions = data.get("current_condition")
            if not current_conditions or not isinstance(current_conditions, list):
                return f"Weather data unavailable for '{location}'."

            current = current_conditions[0]

            temp = current.get("temp_C", "N/A")
            feels_like = current.get("FeelsLikeC", "N/A")
            humidity = current.get("humidity", "N/A")
            wind = current.get("windspeedKmph", "N/A")

            desc_block = current.get("weatherDesc", [])
            desc = (
                desc_block[0].get("value")
                if desc_block and isinstance(desc_block, list)
                else "Unknown"
            )

            location_display = location.title()

            return (
                f"Live environment readings for {location_display}:\n"
                f"- Condition: {desc}\n"
                f"- Temperature: {temp}°C (Feels like: {feels_like}°C)\n"
                f"- Humidity: {humidity}%\n"
                f"- Wind Speed: {wind} km/h"
            )

        except urllib.error.URLError:
            return "Network error: Unable to reach weather service."
        except TimeoutError:
            return "Weather service request timed out."
        except Exception as e:
            return f"Weather extraction failure for '{location}': {str(e)}"

    # ================================================================
    # WEB SEARCH
    # ================================================================
    @staticmethod
    def live_web_search(query: str) -> bool:
        """
        Opens default browser with DuckDuckGo search query.
        Returns True if browser launch attempt was made.
        """
        try:
            query = (query or "").strip()
            if not query:
                print("[LIVE TOOLS]: Empty search query ignored.")
                return False

            clean_query = urllib.parse.quote(query)
            search_url = f"https://duckduckgo.com/?q={clean_query}"

            webbrowser.open(search_url, new=2)  # new=2 → open in new tab
            return True

        except Exception as e:
            print(f"[LIVE TOOLS ERROR]: Failed to open browser: {str(e)}")
            return False