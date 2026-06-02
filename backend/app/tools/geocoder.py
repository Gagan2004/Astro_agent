import logging
import re
import time
from typing import Dict, Any, Optional
import requests
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)

# Predefined reference cities for instant, offline, rate-limit-safe geocoding (crucial for evals)
LOCAL_CITIES: Dict[str, Dict[str, Any]] = {
    "new delhi": {"lat": 28.6139, "lng": 77.2090, "timezone": "Asia/Kolkata", "display_name": "New Delhi, Delhi, India"},
    "delhi": {"lat": 28.6139, "lng": 77.2090, "timezone": "Asia/Kolkata", "display_name": "Delhi, India"},
    "mumbai": {"lat": 19.0760, "lng": 72.8777, "timezone": "Asia/Kolkata", "display_name": "Mumbai, Maharashtra, India"},
    "bombay": {"lat": 19.0760, "lng": 72.8777, "timezone": "Asia/Kolkata", "display_name": "Mumbai, Maharashtra, India"},
    "bengaluru": {"lat": 12.9716, "lng": 77.5946, "timezone": "Asia/Kolkata", "display_name": "Bengaluru, Karnataka, India"},
    "bangalore": {"lat": 12.9716, "lng": 77.5946, "timezone": "Asia/Kolkata", "display_name": "Bengaluru, Karnataka, India"},
    "kolkata": {"lat": 22.5726, "lng": 88.3639, "timezone": "Asia/Kolkata", "display_name": "Kolkata, West Bengal, India"},
    "calcutta": {"lat": 22.5726, "lng": 88.3639, "timezone": "Asia/Kolkata", "display_name": "Kolkata, West Bengal, India"},
    "chennai": {"lat": 13.0827, "lng": 80.2707, "timezone": "Asia/Kolkata", "display_name": "Chennai, Tamil Nadu, India"},
    "madras": {"lat": 13.0827, "lng": 80.2707, "timezone": "Asia/Kolkata", "display_name": "Chennai, Tamil Nadu, India"},
    "london": {"lat": 51.5074, "lng": -0.1278, "timezone": "Europe/London", "display_name": "London, Greater London, England, United Kingdom"},
    "new york": {"lat": 40.7128, "lng": -74.0060, "timezone": "America/New_York", "display_name": "New York, United States"},
    "new york city": {"lat": 40.7128, "lng": -74.0060, "timezone": "America/New_York", "display_name": "New York City, New York, United States"},
    "nyc": {"lat": 40.7128, "lng": -74.0060, "timezone": "America/New_York", "display_name": "New York City, New York, United States"},
    "san francisco": {"lat": 37.7749, "lng": -122.4194, "timezone": "America/Los_Angeles", "display_name": "San Francisco, California, United States"},
    "sf": {"lat": 37.7749, "lng": -122.4194, "timezone": "America/Los_Angeles", "display_name": "San Francisco, California, United States"},
    "los angeles": {"lat": 34.0522, "lng": -118.2437, "timezone": "America/Los_Angeles", "display_name": "Los Angeles, California, United States"},
    "la": {"lat": 34.0522, "lng": -118.2437, "timezone": "America/Los_Angeles", "display_name": "Los Angeles, California, United States"},
    "tokyo": {"lat": 35.6762, "lng": 139.6503, "timezone": "Asia/Tokyo", "display_name": "Tokyo, Japan"},
    "paris": {"lat": 48.8566, "lng": 2.3522, "timezone": "Europe/Paris", "display_name": "Paris, France"},
    "berlin": {"lat": 52.5200, "lng": 13.4050, "timezone": "Europe/Berlin", "display_name": "Berlin, Germany"},
    "sydney": {"lat": -33.8688, "lng": 151.2093, "timezone": "Australia/Sydney", "display_name": "Sydney, New South Wales, Australia"},
    "toronto": {"lat": 43.6532, "lng": -79.3832, "timezone": "America/Toronto", "display_name": "Toronto, Ontario, Canada"},
    "dubai": {"lat": 25.2048, "lng": 55.2708, "timezone": "Asia/Dubai", "display_name": "Dubai, United Arab Emirates"},
    "singapore": {"lat": 1.3521, "lng": 103.8198, "timezone": "Asia/Singapore", "display_name": "Singapore"},
    "auckland": {"lat": -36.8485, "lng": 174.7633, "timezone": "Pacific/Auckland", "display_name": "Auckland, New Zealand"},
}

tf_finder = None

def get_timezone_finder():
    global tf_finder
    if tf_finder is None:
        tf_finder = TimezoneFinder()
    return tf_finder

def geocode_place(place_name: str) -> Optional[Dict[str, Any]]:
    """
    Resolves a place name to latitude, longitude, and timezone.
    First checks local cached dictionary of major cities, then falls back to Open-Meteo Geocoding API.
    """
    if not place_name or not isinstance(place_name, str):
        return None
        
    cleaned_name = place_name.strip().lower()
    
    # Try exact match or prefix match on local cache.
    # NOTE: Use word-boundary matching to avoid false positives like "la paz" -> "la" (Los Angeles).
    for city_key, data in LOCAL_CITIES.items():
        # Exact match
        if cleaned_name == city_key:
            match = True
        # "paris, france" starts with "paris,"
        elif cleaned_name.startswith(city_key + ","):
            match = True
        else:
            # Word-boundary check: city_key must appear as a whole word, not a substring of a word
            # e.g. "la" should NOT match inside "la paz" → it should, but only as a whole token.
            # We require city_key tokens to be present as whole tokens in cleaned_name.
            city_tokens = set(city_key.split())
            name_tokens = set(re.split(r'[\s,]+', cleaned_name))
            match = city_tokens and city_tokens.issubset(name_tokens) and len(city_key) >= 4
        
        if match:
            logger.info(f"Geocoding cache hit for '{place_name}': {data}")
            # Wrap cache hit in the same structure to remain consistent
            return {
                "lat": data["lat"],
                "lng": data["lng"],
                "timezone": data["timezone"],
                "display_name": data["display_name"],
                "results": [data]
            }
            
    # Fallback to Open-Meteo Geocoding API (with simple retry on transient errors)
    logger.info(f"Geocoding cache miss for '{place_name}'. Querying Open-Meteo Geocoding API...")
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        last_exc = None
        response = None
        for attempt in range(3):
            try:
                response = requests.get(
                    url,
                    params={"name": place_name, "count": 10, "language": "en"},
                    timeout=8,
                )
                response.raise_for_status()
                break  # success
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                logger.warning(f"Open-Meteo attempt {attempt + 1}/3 failed for '{place_name}': {exc}")
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
        if response is None:
            raise last_exc

        data = response.json()
        
        results_list = data.get("results")
        if results_list:
            candidates = []
            for item in results_list:
                lat = item.get("latitude")
                lng = item.get("longitude")
                tz_name = item.get("timezone")
                
                # Resolve timezone if missing using timezonefinder
                if not tz_name:
                    tf = get_timezone_finder()
                    tz_name = tf.timezone_at(lng=lng, lat=lat) or "UTC"
                
                name = item.get("name", "")
                admin1 = item.get("admin1", "")
                country = item.get("country", "")
                parts = [p for p in [name, admin1, country] if p]
                display_name = ", ".join(parts)
                
                candidates.append({
                    "lat": lat,
                    "lng": lng,
                    "timezone": tz_name,
                    "display_name": display_name
                })
            
            best = candidates[0]
            result = {
                "lat": best["lat"],
                "lng": best["lng"],
                "timezone": best["timezone"],
                "display_name": best["display_name"],
                "results": candidates
            }
            logger.info(f"Open-Meteo resolved '{place_name}' to {len(candidates)} candidates. Best: {best}")
            return result
        else:
            logger.warning(f"Open-Meteo failed to resolve '{place_name}'")
            return None
    except Exception as e:
        logger.error(f"Geocoding API error for '{place_name}': {str(e)}")
        # If API fails, fall back to a looser substring match in cache as a last resort.
        # Use the same word-boundary logic as primary cache to avoid bad matches.
        for city_key, data in LOCAL_CITIES.items():
            city_tokens = set(city_key.split())
            name_tokens = set(re.split(r'[\s,]+', cleaned_name))
            if city_tokens and city_tokens.issubset(name_tokens) and len(city_key) >= 4:
                logger.info(f"Geocoding recovery cache match for '{place_name}': {data}")
                return {
                    "lat": data["lat"],
                    "lng": data["lng"],
                    "timezone": data["timezone"],
                    "display_name": data["display_name"],
                    "results": [data]
                }
        return None
