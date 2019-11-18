# qgsopenscope
A QGIS plugin that adds import/export functions for openScope airports. This plugin automates the methods detailed in the openScope documentation
[Terrain Generation](https://github.com/openscope/openscope/tree/develop/documentation).

## Table of Contents
- [Table of Contents](#table-of-contents)
- [Caveats](#caveats)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
  * [Installing from Source](#installing-from-source)
    + [Clone this repository and install it from the CLI](#clone-this-repository-and-install-it-from-the-cli)
      - [Install QGIS 3.4](#install-qgis-34)
      - [Configure the environment](#configure-the-environment)
  * [Intalling from Release](#intalling-from-release)
  * [Download and unzip the NOAA GSHHG database](#download-and-unzip-the-noaa-gshhg-database)
- [Usage](#usage)
  * [Configure the QgsOpenScope plugin](#configure-the-qgsopenscope-plugin)
  * [Loading openScope airport files](#loading-openscope-airport-files)
  * [Generating terrain](#generating-terrain)
  * [Modifying water polygons](#modifying-water-polygons)
  * [Other plugin features](#other-plugin-features)

<small><i><a href='http://ecotrust-canada.github.io/markdown-toc/'>Table of contents generated with markdown-toc</a></i></small>

## Caveats
**This plugin is in development, and cannot be assumed to be reliable. Use at your own peril!. Always open a blank project before running any of the functions as it will remove any existing layers from the canvas.**

I'm not a Python developer, so please be aware that some of the code may make your eyes bleed.

## Features
* Import geographical features from an openScope airport into a QGIS project.
* Automatically downloads elevation data and generates contours
* Imports shorelines and lakes from the [NOAA GSHHG](https://www.ngdc.noaa.gov/mgg/shorelines/) to generate water polygons
* Generates Airspace, Fix, Map JSON from the project
* Generates GeoJSON terrain files for the airport
* Generates Restricted airspace JSON
* Tools for generating circles and extended runway centrelines

Planned features:
* Exporting selected Fixes
* RNAV Fix generation

## Requirements
* [QGIS 3.4+](https://qgis.org/en/site/) Lower versions of QGIS 3.x may work, haven't been tried.
It's advisable to use the Long term release (LTR) of QGIS (v.3.4) as likely to be the most stable version
* The NOAA GSHHG shapefiles. The current (v.2.3.7) version can be [downloaded here](https://www.ngdc.noaa.gov/mgg/shorelines/data/gshhg/latest/gshhg-shp-2.3.7.zip)

## Installation
The plugin can be installed in two ways:
1. Clone this repository and install it from the CLI
2. Download the plugin zip file from releases and install from the QGIS Plugin Manager
See [Installing and using the QgsOpenScope plugin for QGIS](https://www.youtube.com/watch?v=V0A83VNzLCU)

### Installing from Source

#### Clone this repository and install it from the CLI
These instructions are for Ubuntu Linux, modify accordingly depending on your distro of choice.

##### Install QGIS 3.4
If you don't have QGIS installed, you can use [instructions provided](https://qgis.org/en/site/forusers/download.html). The plugin has been developed on 3.4 Madeira (LTR). Add the following file to `/etc/apt/sources.list.d/`. eg. for Ubuntu 18.03 (Bionic Beaver):
```
# /etc/apt/sources.list.d/qgis.list
deb     https://qgis.org/ubuntu-ltr bionic main
deb-src https://qgis.org/ubuntu-ltr bionic main
```

Update the packages and install
``` bash
# Add the key, as provided by the QGIS instructions
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key <KEY>

# Update the packages
sudo apt-get update

# Install the required packages
sudo apt-get install qgis
```

##### Configure the environment
Install prerequisites
``` bash
sudo apt-get install git python3-pip python3-setuptools pyqt5-dev-tools

python3 -m pip install wheel pb_tool
```
Make sure `~/.local/bin` is in your PATH variable, as that is where pb_tool is located
``` bash
export PATH=$PATH:~/.local/bin
```

Enter the plugin directory and deploy.
``` bash
# Deploy expects the plugins directory to exist, so the first time
mkdir -p ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins

pb_tool deploy
```

It's advisable to install the experimental QGIS Plugin Reloader plugin. This will enable you to reload the plugin without restarting QGIS ~~if~~ when things go wrong.

### Installing from Release

The plugin must be installed manually as it has not been published in the QGIS plugin repository. See also the
YouTube video - [Installing and using the QgsOpenScope plugin for QGIS](https://www.youtube.com/watch?v=V0A83VNzLCU)

1. Download the QgsOpenScope plugin from the [GitGub website](https://github.com/openscope/qgsopenscope/releases)
2. Open QGIS and navigate to `Plugins->Manage and install plugins...`
3. Select `Install from ZIP file`, and select the ZIP file you just downloaded

### Download and unzip the NOAA GSHHG database

The NOAA provide shorelines, lakes and waterway data in the form of the Global Self-consistent, Hierarchical, High-resolution Geography
Database (GSHHG). These are required by the QgsOpenScope plugin in order to generate water polygons.

1. Download the [GSHHG Shapefiles](https://www.ngdc.noaa.gov/mgg/shorelines/data/gshhg/latest/gshhg-shp-2.3.7.zip)
2. Unzip the `GSHHS_shp/f` to a location of your choice
3. The plugin only uses files in the `GSHHS_shp/f` directory. All other files aren't needed (altough they're interesting to look at)

## Usage

The YouTube video [Installing and using the QgsOpenScope plugin for QGIS](https://www.youtube.com/watch?v=V0A83VNzLCU) demonstrates how to install, configure and
use the plugin.

### Configure the QgsOpenScope plugin

Before being used, the plugin needs to know the location of the GSHHG files

1. Navigate to `Plugins->QgsOpenScope->QgsOpenScope Settings`
2. Specify the path to the openScope airport JSON files, this isn't strictly necessary but makes things quicker to load airports
3. Optionally update the path that is used for storing temp files, this should default to the OS default
4. Specify the path the the GSHHG shapefiles. **Note: this is the path that contains the GSHHS_shp directory**

### Loading openScope airport files

Navigate to `Plugins->QgsOpenScope->Load Airport`, select the airport you want to load. The plugin will clear any existing layers
(it will prompt you to confirm), and will generate the following items:

* Fixes
* Restricted
* Maps
   - One layer for every MapModel in the `maps` property
* Terrain
   - Existing Terrain (if found)
* Airspace
* Airspace (Hidden) (taken from the `_airspace` property)

### Generating terrain

Terrain generation is as simple, albeit slower as the plugin will need to download the height files, and more processing time is required.

1. Select a polygon that will represents the bounds of the terrain. This will usually be the largest (or only polygon) in the Airspace layer
2. Navigate to `Plugins->QgsOpenScope->Generate Terrain`, and select the airport file (this should be the file you last opened)
3. Wait... this can take some time as it's a CPU intensive process
4. Two more layers should be added to the Terrain group:
    - Water
    - Contours - Final

### Modifying water polygons

In some cases (KSFO, KSEA for example), the video map will already have coastline data. Rather than modifying the video maps, the water polygons
are required to be modified to coincided with the video map. This uses two QGIS functions:

* The [Reshape Feature](https://docs.qgis.org/3.4/en/docs/user_manual/working_with_vector/editing_geometry_attributes.html#reshape-features)
* Clipping, including the the [Automatic Tracing tool](https://docs.qgis.org/3.4/en/docs/user_manual/working_with_vector/editing_geometry_attributes.html?highlight=trace#automatic-tracing)

The tools aren't the most intuitive to use, so it's worth reading the QGIS documentation in the links above. The YouTube video [Reshaping water polygons to match the video map](https://youtu.be/5-rSBTLS3kA) demonstrates how this can be done:

1. Select the layer you want to edit (this will most likely be the `Water` layer)
2. Enable editing of the layer (either from the Toolbar, or from the Layer context menu)
3. Select the `Reshape Features` tool from the `Advanced Digitizing Toolbar`
4. `Enable Snapping` (Keyboard `S`) from the `Snapping Toolbar`
5. Optionally `Enable Snapping on Intersection` from the `Snapping Toolbar`
6. Optionally `Enable Tracing` (Keyboard `T`) from the `Snapping Toolbar`

**Note: It's advisable to reshape the polygon in shorter segments, this avoids some frustration if the tool fails to work as expected**

The key part of using the shaping tools is that _"For it to work, the reshape tool’s line must cross the polygon’s boundary at least twice."_
eg. The start and end points should be on the opposite side of the polygon edge that the line you want to reshape to is on.

![Reshaping Features](./doc/QGIS%20-%20Reshape%20Polygon%20to%20Line.gif)

It gets very tedious having to click on every vertex. This is where the `Tracing` tool is helpful. Instead of having to click on every point, you simply have to enable it (Keyboard `T`) and then click on a vertex along the line. Some notes on using the tool:

* Avoid tracing long segments
* When tracing, hide the all layers other than the one you are tracing. The reduces the change of the tool getting _"lost"_

### Other plugin features

As well as automatic loading of features and terrain generation, the plugin also has the following features. The YouTube video [Installing and using the QgsOpenScope plugin for QGIS](https://youtu.be/V0A83VNzLCU?t=136) demonstrates how to use these tools.

* Circle generation
* Extended runway centreline generation
* Exporting of Fixes, Restricted Airspace, Airspace, Maps, Terrain
