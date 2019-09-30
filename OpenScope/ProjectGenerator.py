"""The project generator."""
import os
import tempfile
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsFeature, QgsFeatureRequest, QgsField,
    QgsGeometry,
    QgsMarkerSymbol,
    QgsPalLayerSettings, QgsProject,
    QgsRasterLayer, QgsRectangle,
    QgsVectorLayer, QgsVectorLayerSimpleLabeling, QgsVectorFileWriter
)
from qgis.utils import iface
import processing # pylint: disable=import-error
from .dem import getDemFromLayer

_MEMORY_OUTPUT = 'memory:'

class ProjectGeneratorConfig:
    """The configuration options passed to the ProjectGenerator constructor."""

    contourInterval = 304.8

    gshhsPath = None

    tmpPath = tempfile.gettempdir()

class ProjectGenerator:
    """The project generator."""

    _airport = None

    _config = None

#------------------- Lifecycle -------------------

    def __init__(self, airport, config):
        self._airport = airport
        self._config = config

#------------------- Public -------------------

    def getAirport(self):
        """Gets the AirportModel."""
        return self._airport

    def getAirportPath(self):
        """Gets the location of where temporary files for the airport should be stored."""
        path = os.path.join(self.getTempPath(), self.getIcao())
        os.makedirs(path, exist_ok=True)
        return path

    def getDemsPath(self):
        """Gets the location of where DEM files should be stored."""
        path = os.path.join(self.getTempPath(), 'dems')
        os.makedirs(path, exist_ok=True)
        return path

    def getIcao(self):
        """Gets the ICAO code of the airport."""
        return self.getAirport().getIcao()

    def getTempPath(self):
        """Gets the temporary directory."""
        return os.path.join(self._config.tmpPath, 'qgsopenscope')

    def populateProject(self, _feedback=None):
        """Populates the project."""
        QgsProject.instance().clear()

        root = QgsProject.instance().layerTreeRoot()

        self._generateFixes(root)
        self._generateRestricted(root)

        maps = self._addGroup('Maps')
        self._addGroup('Terrain')

        self._generateAirspace(root)
        self._generateAirspace(root, True)
        self._generateMaps(maps)
        # self._generateTerrain(terrain, airspaceLayer, feedback)

        self._zoomToAllLayers()

#------------------- Private -------------------

    def _addGroup(self, name, parent=None):
        """Add a group to the project's layer tree."""
        if not parent:
            parent = QgsProject.instance().layerTreeRoot()
        return parent.addGroup(name)

    def _addLayerToGroup(self, layer, group):
        """Add the layer to the specified group."""
        QgsProject.instance().addMapLayer(layer, False)
        group.addLayer(layer)

    def _createMemoryLayer(self, name, layerType, fields=None):
        """Creates a new in-memory QgsVectorLayer."""
        layer = QgsVectorLayer('%s?crs=epsg:4326' % layerType, name, 'memory')

        if fields is not None:
            layer.dataProvider().addAttributes(fields)
            layer.updateFields()

        return layer

    def _createVectorLayer(self, name, layerType, fields=None, fileName=None):
        """Creates a new QgsVectorLayer."""
        if not fileName:
            fileName = name
        fileName = os.path.join(self.getAirportPath(), '%s.gpkg' % fileName)

        layer = self._createMemoryLayer(name, layerType, fields)

        QgsVectorFileWriter.writeAsVectorFormat(
            layer,
            fileName,
            'utf-8',
            layer.crs(),
            'GPKG'
        )

        return QgsVectorLayer(fileName, name)

    def _generateAirspace(self, group, hiddenAirspace=False):
        """Generate the Airspace layer."""
        fields = [
            QgsField('name', QVariant.String),
            QgsField('airspace_class', QVariant.String),
            QgsField('floor', QVariant.Int),
            QgsField('ceiling', QVariant.Int)
        ]
        layerName = 'Airspace (Hidden)' if hiddenAirspace else 'Airspace'
        layer = self._createVectorLayer(layerName, 'Polygon', fields)
        features = []

        for a in self.getAirport().getAirspace(hiddenAirspace):
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolygonXY([a.poly]))
            feature.setAttributes([
                None, # ID
                a.name,
                a.airspaceClass,
                a.floor,
                a.ceiling
            ])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        # Colour
        layer.renderer().symbol().setColor(QColor.fromRgb(0x00, 0xff, 0x00))

        # Labeling
        settings = QgsPalLayerSettings()
        settings.fieldName = """coalesce(\"name\", 'No Name') || ' - ' ||
        'FL' || \"floor\" || ' to ' || 'FL' || \"ceiling\" ||
        ' (Class ' || \"airspace_class\" || ')'"""
        settings.isExpression = True
        settings.placement = QgsPalLayerSettings.PerimeterCurved
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)
        layer.triggerRepaint()

        self._addLayerToGroup(layer, group)

        return layer

    def _generateFixes(self, group):
        """Generate the Fixes layer."""
        fields = [
            QgsField('name', QVariant.String),
        ]
        layer = self._createVectorLayer('Fixes', 'Point', fields)
        features = []

        for p in self.getAirport().getFixes():
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPointXY(p.location))
            feature.setAttributes([
                None,
                p.name
            ])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        # Symbol
        symbol = QgsMarkerSymbol.createSimple({
            'name': 'equilateral_triangle',
            'color': 'white',
            'stroke': 'black',
            'size': '3'
        })
        layer.renderer().setSymbol(symbol)

        # Labeling
        settings = QgsPalLayerSettings()
        settings.fieldName = '"name"'
        settings.isExpression = True
        settings.placement = QgsPalLayerSettings.OverPoint
        settings.quadOffset = QgsPalLayerSettings.QuadrantAboveRight
        settings.distance = '1'
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)
        layer.triggerRepaint()

        self._addLayerToGroup(layer, group)

    def _generateMaps(self, group):
        """Generates the Map layers."""
        for m in self.getAirport().getMaps():
            layer = self._createVectorLayer(m.name, 'LineString', fileName='Map - %s' % m.name)
            features = []

            for l in m.lines:
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPolylineXY(l))
                features.append(feature)

            layer.dataProvider().addFeatures(features)

            sym = layer.renderer().symbol()
            sym.setColor(QColor.fromRgb(0x00, 0x00, 0x00))
            sym.setWidth(0.33)

            self._addLayerToGroup(layer, group)

    def _generateRestricted(self, group):
        """Generate the Restricted layer."""
        fields = [
            QgsField('name', QVariant.String),
            QgsField('height', QVariant.String),
        ]
        layer = self._createVectorLayer('Restricted', 'Polygon', fields)
        features = []

        for r in self.getAirport().getRestricted():
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPolygonXY([r.coordinates]))
            feature.setAttributes([
                None, # ID
                r.name,
                r.height
            ])
            features.append(feature)

        layer.dataProvider().addFeatures(features)

        # Colour
        layer.renderer().symbol().setColor(QColor.fromRgb(0xff, 0x60, 0x60))

        # Labeling
        settings = QgsPalLayerSettings()
        settings.fieldName = '"name" || \'\\n0ft\\n\' || "height"'
        settings.isExpression = True
        settings.placement = QgsPalLayerSettings.AroundPoint
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)
        layer.triggerRepaint()

        self._addLayerToGroup(layer, group)

        return layer

    def _generateTerrain(self, group, airspace, feedback):
        """Generate the terrain."""
        # Get the clipping bounds
        perimeter, buffer = self._getAirspace(airspace)
        # self._addLayerToGroup(airspace, group)
        # self._addLayerToGroup(perimeter, group)
        # self._addLayerToGroup(buffer, group)

        # Get the water
        water = self._getWater(airspace, buffer)
        self._addLayerToGroup(water, group)

        # Height data
        mergedDem, clippedDem, contours = self._getElevationData(buffer, feedback)
        # self._addLayerToGroup(mergedDem, group)
        # self._addLayerToGroup(clippedDem, group)
        # self._addLayerToGroup(contours, group)

        # Clean the contours
        cleaned = self._getCleanContours(contours, perimeter, airspace)
        self._addLayerToGroup(cleaned, group)

        # Normalize the contours
        self._normalizeContours(cleaned, clippedDem)

        # Clean up unused layers
        for l in [mergedDem, clippedDem, contours]:
            del l

    def _getAirspace(self, airspace):
        """Generate the Airspace layer."""
        # Perimeter
        result = processing.run('qgis:polygonstolines', {
            'INPUT': airspace,
            'OUTPUT': _MEMORY_OUTPUT
        })
        perimeter = result['OUTPUT']
        perimeter.setName('Perimeter')

        # Buffer the airspace
        result = processing.run('qgis:buffer', {
            'INPUT': airspace,
            'OUTPUT': _MEMORY_OUTPUT,
            'DISTANCE': 0.005
        })
        buffer = result['OUTPUT']
        buffer.setName('Buffer')

        return (perimeter, buffer)

    def _getCleanContours(self, contours, perimeter, airspace):
        """Get the cleaned contours."""
        # Simplify the contours
        result = processing.run('qgis:simplifygeometries', {
            'INPUT': contours,
            'TOLERANCE': 0.002,
            'OUTPUT': _MEMORY_OUTPUT
        })
        simplified = result['OUTPUT']
        simplified.setName('Contours - Simplified')

        # Merge with perimeter
        result = processing.run('qgis:mergevectorlayers', {
            'LAYERS': [simplified, perimeter],
            'OUTPUT': _MEMORY_OUTPUT
        })
        merged = result['OUTPUT']
        merged.setName('Contours - Merged')

        # Polygonise
        result = processing.run('qgis:polygonize', {
            'INPUT': merged,
            'OUTPUT': _MEMORY_OUTPUT,
        })
        polygons = result['OUTPUT']
        polygons.setName('Contours - Polygons')

        # Select all polygons smaller than 0.0005 sq degrees (about 38ha at lat=52))
        # and eliminate them
        selection = polygons.getFeatures(QgsFeatureRequest().setFilterExpression('$area < 0.00005'))
        polygons.selectByIds([k.id() for k in selection])

        result = processing.run('qgis:eliminateselectedpolygons', {
            'INPUT': polygons,
            'OUTPUT': _MEMORY_OUTPUT,
            'MODE': 2 # Largest common boundary
        })
        cleaned = result['OUTPUT']
        cleaned.setName('Contours - Cleaned')

        # Delete any features that weren't eliminated (outside a common boundary)
        selection = cleaned.getFeatures(QgsFeatureRequest().setFilterExpression('$area < 0.00005'))
        cleaned.dataProvider().deleteFeatures([k.id() for k in selection])

        # Clip to airspace
        result = processing.run('qgis:clip', {
            'INPUT': cleaned,
            'OUTPUT': _MEMORY_OUTPUT,
            'OVERLAY': airspace
        })
        clipped = result['OUTPUT']
        clipped.setName('Contours - Clipped')

        # Multipart to single part
        result = processing.run('qgis:multiparttosingleparts', {
            'INPUT': clipped,
            'OUTPUT': _MEMORY_OUTPUT
        })
        final = result['OUTPUT']
        final.setName('Contours - Final')

        # Styling
        final.renderer().symbol().setColor(QColor.fromRgb(0xff, 0x9e, 0x17))

        return final

    def _getContourInterval(self):
        """Get the contour interval (in metres)."""
        return self._config.contourInterval

    def _getElevationData(self, boundingLayer, feedback):
        """Get the elevation layers."""
        demFiles = getDemFromLayer(self.getDemsPath(), boundingLayer)

        airportPath = self.getAirportPath()

        # Merge all the DEM files into a single geotiff
        mergedFile = os.path.join(airportPath, 'Elevation - Merged.tif')
        if os.path.isfile(mergedFile):
            os.unlink(mergedFile)

        result = processing.run('gdal:merge', {
            'INPUT': demFiles,
            'DATA_TYPE': 1,
            'OUTPUT': mergedFile
        }, feedback)
        merged = QgsRasterLayer(result['OUTPUT'], 'Elevation - Merged')

        # Clip the DEM file to the bounds
        clippedFile = os.path.join(airportPath, 'Elevation - Clipped.tif')
        if os.path.isfile(clippedFile):
            os.unlink(clippedFile)

        result = processing.run('gdal:cliprasterbymasklayer', {
            'INPUT': mergedFile,
            'MASK': boundingLayer,
            'OUTPUT': clippedFile
        }, feedback)
        clipped = QgsRasterLayer(result['OUTPUT'], 'Elevation - Clipped')

        # Generate the contours
        contourFile = os.path.join(airportPath, 'Contours.shp')
        if os.path.isfile(contourFile):
            os.unlink(contourFile)

        result = processing.run('gdal:contour', {
            'INPUT': clippedFile,
            'BAND' : 1,
            'INTERVAL': self._getContourInterval(),
            'OUTPUT': contourFile
        })
        contours = QgsVectorLayer(result['OUTPUT'], 'Contours')

        return (merged, clipped, contours)

    def _getWater(self, airspace, buffer):
        """Get the water layer."""
        gshhsPath = self._config.gshhsPath

        coastlines = QgsVectorLayer(os.path.join(gshhsPath, 'GSHHS_shp/f/GSHHS_f_L1.shp'), 'Coastline')
        lakes = QgsVectorLayer(os.path.join(gshhsPath, 'GSHHS_shp/f/GSHHS_f_L2.shp'), 'Lakes')

        # Clip by the buffer
        result = processing.run('qgis:clip', {
            'INPUT': coastlines,
            'OVERLAY': buffer,
            'OUTPUT': _MEMORY_OUTPUT
        })
        clipped_coastlines = result['OUTPUT']

        result = processing.run('qgis:clip', {
            'INPUT': lakes,
            'OVERLAY': buffer,
            'OUTPUT': _MEMORY_OUTPUT
        })
        clipped_lakes = result['OUTPUT']

        # Simplify
        result = processing.run('qgis:simplifygeometries', {
            'INPUT': clipped_coastlines,
            'TOLERANCE': 0.002,
            'OUTPUT': _MEMORY_OUTPUT
        })
        cleaned = result['OUTPUT']

        # Delete any small islands
        it = cleaned.getFeatures(QgsFeatureRequest().setFilterExpression("$area < 0.0005"))
        cleaned.dataProvider().deleteFeatures([i.id() for i in it])

        # Invert to get the water
        result = processing.run('qgis:difference', {
            'INPUT': buffer,
            'OVERLAY': cleaned,
            'OUTPUT': _MEMORY_OUTPUT
        })
        difference = result['OUTPUT']

        # Merge sea with lakes
        result = processing.run('qgis:mergevectorlayers', {
            'LAYERS': [difference, clipped_lakes],
            'OUTPUT': _MEMORY_OUTPUT
        })
        merged_water = result['OUTPUT']

        # Re-clip by the airspace
        result = processing.run('qgis:clip', {
            'INPUT': merged_water,
            'OVERLAY': airspace,
            'OUTPUT': _MEMORY_OUTPUT
        })
        clipped = result['OUTPUT']

        # Multipart to single part
        result = processing.run('qgis:multiparttosingleparts', {
            'INPUT': clipped,
            'OUTPUT': _MEMORY_OUTPUT
        })
        water = result['OUTPUT']
        water.setName('Water')

        # Delete any small area of water
        it = water.getFeatures(QgsFeatureRequest().setFilterExpression("$area < 0.0005"))
        water.dataProvider().deleteFeatures([i.id() for i in it])

        # Add an elevation attribute (0)
        water.startEditing()
        water.addAttribute(QgsField("elevation", QVariant.Double))
        elevationIndex = water.fields().indexFromName('elevation')
        for f in water.getFeatures():
            f[elevationIndex] = 0
            water.updateFeature(f)
        water.commitChanges()

        # Styling
        water.renderer().symbol().setColor(QColor.fromRgb(0x00, 0xff, 0xff))

        return water

    def _normalizeContours(self, contours, elevation):
        """Normalize the contours."""
        # Calculate zonal statistics
        processing.run('qgis:zonalstatistics', {
            'INPUT_RASTER': elevation,
            'INPUT_VECTOR': contours,
            'RASTER_BAND': 1,
            'STATS' : [2], # mean
            'COLUMN_PREFIX' : '_'
        })

        contourInterval = self._getContourInterval()

        # Remove any polygons lower than the altitude interval
        it = contours.getFeatures(QgsFeatureRequest().setFilterExpression('_mean < %f' % contourInterval))
        contours.dataProvider().deleteFeatures([i.id() for i in it])

        # Add a virtual field containing the normalised height to the altitude interval
        field = QgsField('elevation', QVariant.Double)
        contours.addExpressionField('floor(_mean / %(interval)f) * %(interval)f' % {'interval': contourInterval}, field)

    def _zoomToAllLayers(self):
        """Zoom to the buffered area and redraw"""
        canvas = iface.mapCanvas()
        bounds = QgsRectangle()

        for item in QgsProject.instance().layerTreeRoot().findLayers():
            extent = item.layer().extent()

            if not extent.isEmpty():
                bounds.combineExtentWith(extent)

        canvas.setExtent(bounds)
        canvas.refreshAllLayers()
