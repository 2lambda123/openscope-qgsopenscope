import re
from qgis.core import QgsPointXY

EXPORT_PRECISION = 5

_LAT_LNG = re.compile(r'^([NESW])(\d+(\.\d+)?)([d °](\d+(\.\d+)?))?([m \'](\d+(\.\d+)?))?$', re.IGNORECASE)
_SW = re.compile('[SW]', re.IGNORECASE)

#------------------- Public -------------------

def fromPointXY(point):
    """Gets a [lat,lng] item from the specifide QgsPointXY object."""

    lat = point.y()
    lng = point.x()
    ns = 'S' if lat < 0 else 'N'
    ew = 'W' if lng < 0 else 'E'

    return [
        ns + '%02.5f' % abs(lat),
        ew + '%03.5f' % abs(lng),
    ]

def fromPolygon(feature):
    """Takes a Polygon QgsFeature and creates an array of [lat,lng] values."""

    polygon = feature.geometry().asPolygon()[0] # asPolygon returns an array here, use the first item
    points = list(map(lambda point: fromPointXY(point), polygon))

    # Ensure a close polygon isn't returned
    if polygon[0] == polygon[-1]:
        del points[-1]

    return points

def fromPolyline(feature):
    """Takes a Polyline QgsFeature and creates an array of [lat,lng,lat,lng] values."""

    lines = []
    polyline = feature.geometry().asPolyline()
    count = len(polyline) - 1
    i = 0

    while i < count:
        lines.append(fromPointXY(polyline[i]) + fromPointXY(polyline[i + 1]))
        i += 1

    return lines

def fromPolylines(features):
    """Takes an an iterable of QgsFeature objects and creates an array of [lat,lng,lat,lng] values."""

    # Gets a [lat,lng,lat,lng][]
    linesList = list(map(lambda feature: fromPolyline(feature), features))
    
    # Flattens the 2d list
    return [item for lines in linesList for item in lines]

def parseCoordinateValue(value):
    """Parse the specified value into a floating point value.

    This emulates openScope's unitConverter.parseCoordinate method
    """
    if (isinstance(value, float) or isinstance(value, int)):
        return value

    match = _LAT_LNG.match(str(value))
    if (match == None):
        raise(Exception('Cannot parse %s as coordinate' % value))
    
    degrees = float(match.group(2))
    minutes = 0
    seconds = 0
    if (match.group(5) != None):
        minutes = float(match.group(5)) / 60

    if (match.group(8) != None):
        seconds = float(match.group(8)) / 3600
    
    decimalDegrees = degrees + minutes + seconds

    if (_SW.match(match.group(1))):
        decimalDegrees *= -1

    return decimalDegrees

def toPointXY(array, index = 0):
    """Gets the QgsPointXY from the array at the specified index."""
    return QgsPointXY(
        parseCoordinateValue(array[index + 1]), # Longitude
        parseCoordinateValue(array[index + 0]) # Latitude
    )

def toPolygon(values):
    """Parses an array of [lat,lng] values into an array of QPointXY objects"""

    polygon = list(map(lambda x: toPointXY(x), values))

    # Make sure the polygon isn't closed
    if polygon[0] == polygon[-1]:
        del polygon[-1]

    return polygon

def toPolyline(values):
    """Parses an array of [lat,lng,lat,lng...] values into an 2d array of QPointXY objects"""
    
    lines = []

    for item in values:
        points = []
        lastIndex = len(item) - 1
        i = 0

        # Iterate over each of the pairs in the list
        while i < lastIndex:
            points.append(toPointXY(item, i))
            i += 2

        lines.append(points)

    return lines
