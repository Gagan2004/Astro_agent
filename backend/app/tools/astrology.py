import swisseph as swe
import datetime
import re
from typing import Dict, Any, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Zodiac Signs Configuration
ZODIAC_SIGNS = [
    {"name": "Aries", "sanskrit": "Mesha", "symbol": "♈"},
    {"name": "Taurus", "sanskrit": "Vrishabha", "symbol": "♉"},
    {"name": "Gemini", "sanskrit": "Mithuna", "symbol": "♊"},
    {"name": "Cancer", "sanskrit": "Karka", "symbol": "♋"},
    {"name": "Leo", "sanskrit": "Simha", "symbol": "♌"},
    {"name": "Virgo", "sanskrit": "Kanya", "symbol": "♍"},
    {"name": "Libra", "sanskrit": "Tula", "symbol": "♎"},
    {"name": "Scorpio", "sanskrit": "Vrishchika", "symbol": "♏"},
    {"name": "Sagittarius", "sanskrit": "Dhanu", "symbol": "♐"},
    {"name": "Capricorn", "sanskrit": "Makara", "symbol": "♑"},
    {"name": "Aquarius", "sanskrit": "Kumbha", "symbol": "♒"},
    {"name": "Pisces", "sanskrit": "Meena", "symbol": "♓"}
]

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Rahu": swe.MEAN_NODE,  # North Node
}

ASPECTS = [
    {"name": "Conjunction", "angle": 0, "orb": 8, "symbol": "☌", "meaning": "harmonious blending, intensification"},
    {"name": "Sextile", "angle": 60, "orb": 6, "symbol": "⚹", "meaning": "supportive opportunity, easy flow of energy"},
    {"name": "Square", "angle": 90, "orb": 8, "symbol": "□", "meaning": "tension, friction, challenge prompting action"},
    {"name": "Trine", "angle": 120, "orb": 8, "symbol": "△", "meaning": "natural talent, harmony, effortless luck"},
    {"name": "Opposition", "angle": 180, "orb": 8, "symbol": "☍", "meaning": "awareness, polarity, relationship tension, compromise"}
]

def format_longitude(long: float, ayanamsa: float = 0.0) -> Dict[str, Any]:
    """Converts a longitude into Zodiac Sign, degree, minutes, seconds."""
    adjusted_long = (long - ayanamsa) % 360
    sign_index = int(adjusted_long // 30) % 12
    sign_deg = adjusted_long % 30
    
    deg = int(sign_deg)
    min_float = (sign_deg - deg) * 60
    m = int(min_float)
    s = int((min_float - m) * 60)
    
    sign_info = ZODIAC_SIGNS[sign_index]
    
    return {
        "raw_longitude": adjusted_long,
        "sign_name": sign_info["name"],
        "sign_sanskrit": sign_info["sanskrit"],
        "sign_symbol": sign_info["symbol"],
        "sign_index": sign_index,
        "degrees": deg,
        "minutes": m,
        "seconds": s,
        "formatted": f"{deg}° {sign_info['name']} {m}'"
    }

def get_house_for_planet(planet_long: float, cusps: list) -> int:
    """
    Determines which house a planet is in, given its longitude and the 0-indexed 12-element
    house cusps list (each element is the cusp start longitude of houses 1-12).
    Handles boundary wrapping at 360/0 degrees.
    """
    for i in range(12):
        start = cusps[i]
        end = cusps[(i + 1) % 12]
        if start <= end:
            if start <= planet_long < end:
                return i + 1  # Houses are 1-indexed
        else:  # wraps around 360
            if planet_long >= start or planet_long < end:
                return i + 1
    return 1  # Fallback

def _normalize_date(date_str: str) -> str:
    """
    Normalize various date formats to YYYY-MM-DD.
    Handles: 'YYYY-MM-DD', 'YYYY/MM/DD', 'DD/MM/YYYY', 'Month DD YYYY', 'DD Month YYYY', etc.
    """
    date_str = date_str.strip()
    
    # Already in correct format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # YYYY/MM/DD
    m = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})$', date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    
    # DD/MM/YYYY or MM/DD/YYYY — assume DD/MM/YYYY for international
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', date_str)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    # Try dateutil or strptime for natural language dates like 'Jan 1 1990', '1 January 1990'
    MONTH_MAP = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    tokens = re.split(r'[\s,]+', date_str)
    year = month = day = None
    for tok in tokens:
        tok_l = tok.lower()[:3]
        if tok_l in MONTH_MAP:
            month = MONTH_MAP[tok_l]
        elif re.match(r'^\d{4}$', tok):
            year = int(tok)
        elif re.match(r'^\d{1,2}$', tok):
            day = int(tok)
    if year and month and day:
        return f"{year}-{month:02d}-{day:02d}"
    
    raise ValueError(f"Unrecognised date format: '{date_str}'. Expected YYYY-MM-DD.")


def _normalize_time(time_str: str) -> str:
    """
    Normalize time to 24-hour HH:MM format.
    Handles: 'HH:MM', 'H:MM AM/PM', 'HH:MM:SS', '12:00 PM', '12:00PM', etc.
    """
    time_str = time_str.strip()
    
    # Already correct 24h HH:MM
    if re.match(r'^\d{2}:\d{2}$', time_str):
        return time_str

    # HH:MM:SS — strip seconds
    m = re.match(r'^(\d{1,2}):(\d{2}):\d{2}$', time_str)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"

    # 12-hour AM/PM: '12:00 PM', '8:30AM', '8:30 am'
    m = re.match(r'^(\d{1,2}):(\d{2})\s*(am|pm)$', time_str, re.IGNORECASE)
    if m:
        h, mn, meridiem = int(m.group(1)), int(m.group(2)), m.group(3).lower()
        if meridiem == 'am':
            h = 0 if h == 12 else h
        else:
            h = 12 if h == 12 else h + 12
        return f"{h:02d}:{mn:02d}"

    # Just HH:MM with single-digit hour
    m = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"

    raise ValueError(f"Unrecognised time format: '{time_str}'. Expected HH:MM (24h).")


def get_julian_day(date_str: str, time_str: str, tz_offset_hours: float) -> float:
    """
    Computes Julian Day in UT.
    date_str: YYYY-MM-DD (or common variants — will be normalised)
    time_str: HH:MM 24h (or 12h AM/PM — will be normalised)
    tz_offset_hours: Timezone offset in hours (e.g. +5.5 for IST, -5 for EST)
    """
    try:
        date_str = _normalize_date(date_str)
        time_str = _normalize_time(time_str)
        y, m, d = map(int, date_str.split('-'))
        h, mn = map(int, time_str.split(':'))
    except ValueError as e:
        logger.error(f"Error normalising date '{date_str}' or time '{time_str}': {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}' or time '{time_str}': {str(e)}")
        raise ValueError("Invalid date or time format. Expected YYYY-MM-DD and HH:MM.")

    # Check if timezone conversion wrapped date to previous or next day
    dt = datetime.datetime(y, m, d, h, mn)
    dt_utc = dt - datetime.timedelta(hours=tz_offset_hours)
    
    # Calculate Julian Day in UT
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)
    return jd

def compute_birth_chart(
    date_str: str, 
    time_str: str, 
    lat: float, 
    lon: float, 
    tz_offset_hours: float,
    sidereal: bool = False
) -> Dict[str, Any]:
    """
    Given birth parameters, computes the planetary positions and house cusps.
    """
    jd = get_julian_day(date_str, time_str, tz_offset_hours)
    
    # Compute Ayanamsa if sidereal mode is enabled (Vedic Lahiri)
    ayanamsa = 0.0
    if sidereal:
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        ayanamsa = swe.get_ayanamsa_ut(jd)
        logger.info(f"Sidereal mode enabled. Lahiri Ayanamsa: {ayanamsa:.4f} degrees")
        
    # Calculate Planets
    planets_data = {}
    for planet_name, planet_id in PLANETS.items():
        # swe.calc_ut returns (position, return_flag)
        # position: (longitude, latitude, distance, speed_long, speed_lat, speed_dist)
        pos, _ = swe.calc_ut(jd, planet_id)
        raw_long = pos[0]
        
        # Ketu is exactly opposite Rahu (+180 degrees)
        if planet_name == "Rahu":
            ketu_long = (raw_long + 180.0) % 360.0
            planets_data["Rahu"] = format_longitude(raw_long, ayanamsa)
            planets_data["Ketu"] = format_longitude(ketu_long, ayanamsa)
        else:
            planets_data[planet_name] = format_longitude(raw_long, ayanamsa)
            
    # Calculate Houses
    # swe.houses returns (cusps, ascmc)
    # swe.houses() returns 12 cusps (0-indexed) and ascmc array
    # hsys 'P' is Placidus. If Placidus fails (near poles), fall back to Equal 'E'
    try:
        cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    except Exception as e:
        logger.warning(f"Placidus houses failed, falling back to Equal: {str(e)}")
        cusps, ascmc = swe.houses(jd, lat, lon, b'E')

    # cusps is a 12-element tuple: cusp longitudes for houses 1-12 (0-indexed)
    # Apply ayanamsa to houses if sidereal
    adjusted_cusps = [(c - ayanamsa) % 360 for c in cusps]
    ascendant_raw = (ascmc[0] - ayanamsa) % 360
    mc_raw = (ascmc[1] - ayanamsa) % 360
    
    ascendant = format_longitude(ascendant_raw, 0.0)
    mc = format_longitude(mc_raw, 0.0)
    
    # Compile house ranges (adjusted_cusps is 0-indexed: house N = adjusted_cusps[N-1])
    houses_data = []
    for idx in range(12):
        start_cusp = adjusted_cusps[idx]
        end_cusp = adjusted_cusps[(idx + 1) % 12]
        
        start_info = format_longitude(start_cusp, 0.0)
        houses_data.append({
            "house_number": idx + 1,
            "cusp_longitude": start_cusp,
            "sign": start_info["sign_name"],
            "formatted_cusp": start_info["formatted"]
        })
        
    # Map planets to houses (pass the 0-indexed 12-element list)
    for p_name, p_val in planets_data.items():
        h_num = get_house_for_planet(p_val["raw_longitude"], adjusted_cusps)
        p_val["house"] = h_num

    return {
        "jd": jd,
        "ayanamsa": ayanamsa,
        "ascendant": ascendant,
        "mc": mc,
        "planets": planets_data,
        "houses": houses_data,
        "cusps": adjusted_cusps  # 12-element list, houses 1-12
    }

def get_daily_transits(
    transit_date_str: str,
    natal_chart: Dict[str, Any],
    lat: float,
    lon: float,
    sidereal: bool = False
) -> Dict[str, Any]:
    """
    Computes transits for a given date and compares aspects to a user's natal chart.
    """
    # Use 12:00 PM (noon) in UTC as standard reference for daily transits
    jd_transit = get_julian_day(transit_date_str, "12:00", 0.0)
    
    # Compute Ayanamsa for transit date if sidereal
    ayanamsa = 0.0
    if sidereal:
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        ayanamsa = swe.get_ayanamsa_ut(jd_transit)
        
    # Calculate transit planet positions
    transit_planets = {}
    for planet_name, planet_id in PLANETS.items():
        pos, _ = swe.calc_ut(jd_transit, planet_id)
        raw_long = pos[0]
        
        if planet_name == "Rahu":
            ketu_long = (raw_long + 180.0) % 360.0
            transit_planets["Rahu"] = format_longitude(raw_long, ayanamsa)
            transit_planets["Ketu"] = format_longitude(ketu_long, ayanamsa)
        else:
            transit_planets[planet_name] = format_longitude(raw_long, ayanamsa)
            
    # Place transit planets into natal houses
    # natal_chart["cusps"] is already a 0-indexed 12-element list
    natal_cusps = natal_chart["cusps"]
    for tp_name, tp_val in transit_planets.items():
        tp_val["house"] = get_house_for_planet(tp_val["raw_longitude"], natal_cusps)
        
    # Find aspects between transit planets and natal planets
    active_aspects = []
    for tp_name, tp_val in transit_planets.items():
        t_long = tp_val["raw_longitude"]
        
        for np_name, np_val in natal_chart["planets"].items():
            n_long = np_val["raw_longitude"]
            
            diff = abs(t_long - n_long)
            diff = min(diff, 360 - diff)
            
            for aspect in ASPECTS:
                if abs(diff - aspect["angle"]) <= aspect["orb"]:
                    active_aspects.append({
                        "transit_planet": tp_name,
                        "aspect_name": aspect["name"],
                        "aspect_symbol": aspect["symbol"],
                        "natal_planet": np_name,
                        "exactness_diff": round(abs(diff - aspect["angle"]), 2),
                        "meaning": aspect["meaning"]
                    })
                    
    return {
        "transit_date": transit_date_str,
        "transit_planets": transit_planets,
        "aspects": active_aspects
    }
