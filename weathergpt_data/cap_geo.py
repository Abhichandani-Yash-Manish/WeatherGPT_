"""CAP geographic applicability: does an official CAP area cover a user point?

Pure geometry over the areas `foundation.parse_cap` already extracts. It
answers one question per CAP record — applicable / not_applicable / held —
and never authorises dissemination on its own: lifecycle (`cap_lifecycle`),
authenticity, and completeness stay separate, honestly-labelled concerns.

Coordinate order follows OASIS CAP 1.2 §3.2.2 and is the opposite of GeoJSON:
a polygon is "latitude,longitude" pairs, a circle is "latitude,longitude
radius-in-metres". Geocodes are never guessed: without a reviewed
code crosswalk they hold with their codes listed.
"""
import math

EARTH_RADIUS_M = 6371000.0


def parse_polygon(text):
    """A CAP polygon string to [(lat, lon), ...]. Raises ValueError when malformed."""
    if not isinstance(text, str):
        raise ValueError('CAP polygon is not text')
    points = []
    for pair in text.strip().split():
        parts = pair.split(',')
        if len(parts) != 2:
            raise ValueError('CAP polygon pair is not lat,lon: %r' % (pair[:40],))
        try:
            lat, lon = float(parts[0]), float(parts[1])
        except ValueError:
            raise ValueError('CAP polygon pair is not numeric: %r' % (pair[:40],))
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ValueError('CAP polygon pair is outside valid ranges')
        points.append((lat, lon))
    if len(points) < 4:
        raise ValueError('CAP polygon needs at least four points')
    if points[0] != points[-1]:
        points = points + [points[0]]
    return points


def parse_circle(text):
    """A CAP circle string to (lat, lon, radius_m). Raises ValueError when malformed."""
    if not isinstance(text, str):
        raise ValueError('CAP circle is not text')
    parts = text.strip().split()
    if len(parts) != 2:
        raise ValueError('CAP circle is not "lat,lon radius"')
    try:
        lat, lon = (float(piece) for piece in parts[0].split(','))
        radius = float(parts[1])
    except ValueError:
        raise ValueError('CAP circle is not numeric')
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        raise ValueError('CAP circle centre is outside valid ranges')
    if not (radius > 0):
        raise ValueError('CAP circle radius must be positive')
    return lat, lon, radius


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres."""
    to_rad = math.pi / 180.0
    d_lat = (lat2 - lat1) * to_rad
    d_lon = (lon2 - lon1) * to_rad
    arc = (math.sin(d_lat / 2.0) ** 2
           + math.cos(lat1 * to_rad) * math.cos(lat2 * to_rad) * math.sin(d_lon / 2.0) ** 2)
    return 2.0 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(arc)))


def match_polygon(lat, lon, polygon_text):
    """Point-in-polygon using the same covers() rule as the district matcher."""
    from shapely.geometry import Point, Polygon
    try:
        ring = parse_polygon(polygon_text)
    except ValueError as exc:
        return 'held', 'Unusable CAP polygon: ' + str(exc)
    try:
        area = Polygon([(lon, lat) for lat, lon in ring])
    except (ValueError, TypeError):
        return 'held', 'Unusable CAP polygon: geometry construction failed'
    if area.is_empty or not area.is_valid:
        return 'held', 'Unusable CAP polygon: empty or invalid ring'
    if area.covers(Point(float(lon), float(lat))):
        return 'applicable', 'The point falls inside the official CAP polygon.'
    return 'not_applicable', 'The point falls outside the official CAP polygon.'


def match_circle(lat, lon, circle_text):
    """Point-in-circle by geodesic distance against the stated radius."""
    try:
        centre_lat, centre_lon, radius = parse_circle(circle_text)
    except ValueError as exc:
        return 'held', 'Unusable CAP circle: ' + str(exc)
    distance = haversine_m(lat, lon, centre_lat, centre_lon)
    if distance <= radius:
        return 'applicable', 'The point is %.0f m inside the official %.0f m CAP circle.' % (distance, radius)
    return 'not_applicable', 'The point is %.0f m outside the official %.0f m CAP circle.' % (distance, radius)


def match_area(lat, lon, area):
    """One CAP area dict (polygons/circles/geocodes) to (verdict, reason).

    Applicable wins over held wins over not-applicable across the area's
    shapes; geocodes always hold — codes are listed, never guessed.
    """
    if lat is None or lon is None:
        return 'held', 'No user point to test the CAP area against.'
    if not isinstance(area, dict):
        return 'held', 'CAP area is missing or unreadable.'
    verdicts = []
    for polygon in area.get('polygons') or []:
        if polygon:
            verdicts.append(match_polygon(lat, lon, polygon))
    for circle in area.get('circles') or []:
        if circle:
            verdicts.append(match_circle(lat, lon, circle))
    codes = [geocode for geocode in (area.get('geocodes') or []) if geocode]
    if codes:
        verdicts.append(('held', 'CAP geocodes are not mapped without a reviewed code crosswalk: '
                                 + ', '.join(sorted({str(code) for code in codes}))[:200]))
    if not verdicts:
        return 'held', 'The CAP message states no polygon, circle, or geocode to test.'
    for verdict, reason in verdicts:
        if verdict == 'applicable':
            return verdict, reason
    for verdict, reason in verdicts:
        if verdict == 'held':
            return verdict, reason
    return verdicts[0]


def assess_records(records, lat, lon):
    """Per-record applicability over every info block's areas. Never raises.

    Returns [{identifier, sender, verdict, reason}]. Geometry only: time,
    status, and lifecycle eligibility stay with `cap_lifecycle.resolve`.
    A caller must still refuse dissemination on held — held is not a no.
    """
    assessed = []
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return [{'identifier': (record or {}).get('identifier'), 'sender': (record or {}).get('sender'),
                 'verdict': 'held', 'reason': 'No usable user point to test CAP areas against.'}
                for record in records or []]
    for record in records or []:
        record = record or {}
        infos = record.get('info') or []
        area_verdicts = [match_area(lat, lon, area)
                         for info in infos if isinstance(info, dict)
                         for area in (info.get('areas') or [])]
        if not area_verdicts:
            verdict, reason = 'held', 'The CAP message carries no areas to test.'
        else:
            verdict, reason = area_verdicts[0]
            for candidate in area_verdicts[1:]:
                if candidate[0] == 'applicable':
                    verdict, reason = candidate
                    break
                if candidate[0] == 'held' and verdict == 'not_applicable':
                    verdict, reason = candidate
        assessed.append({'identifier': record.get('identifier'), 'sender': record.get('sender'),
                         'verdict': verdict, 'reason': reason})
    return assessed
