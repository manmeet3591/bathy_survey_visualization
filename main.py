import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from geopy.geocoders import Nominatim
from pyproj import CRS
import utm

import pandas as pd
import numpy as np
from scipy.spatial import Delaunay


# ... (Your functions like `get_epsg` go here)
import pyproj

def latlon_to_utm(lat, lon, zone_number, northern):
    proj_utm = pyproj.Proj(proj='utm', zone=zone_number, ellps='WGS84', south=not northern)
    utm_x, utm_y = proj_utm(lon, lat)
    return utm_x, utm_y

def get_epsg(dam_name, country):
  geolocator = Nominatim(user_agent='my_user_agent')
  # get location in lat lon
  loc = geolocator.geocode(dam_name  + ',' + country)
  # get utm zone and utm letter from lat lon
  x, y, utm_zone, letter = utm.from_latlon(loc.latitude, loc.longitude)
  # predefined utm letters
  # https://www.maptools.com/tutorials/grid_zone_details#:~:text=Each%20zone%20is%20divided%20into,spans%2012%C2%B0%20of%20latitude.
  nothern_letters = ('N','P','Q','R','S','T','U','V','W','X')
  southern_letters = ('M','L','K','J','H','G','F','E','D','C')
  # check hemisphere using utm letter
  if letter in nothern_letters:
    hemisphere = 'nothern'
    north_south = True
  else:
    hemisphere = 'southern'
    north_south = False
  # get crs info using utm zone and hemisphere
  crs = CRS.from_dict({'proj': 'utm', 'zone': utm_zone, north_south: True})
  # formatting epsg code into required fromat
  epsg = crs.to_authority()[0] + ':' + crs.to_authority()[1]
  return epsg, hemisphere, north_south

st.title('Bathymetry Survey Visualization')

# File uploader
uploaded_file = st.file_uploader("Choose a file")
if uploaded_file is not None:
    # Assuming the file is a CSV and has no header
    df = pd.read_csv(uploaded_file, header=None)
    
    # User input for dam name and country
    dam_name = st.text_input("Enter Dam Name:", "Tenughat")
    country = st.text_input("Enter Country:", "India")
    
    epsg, hemisphere, north_south = get_epsg(dam_name, country)
    zone = int(epsg[-2:])
    
    # Data preprocessing
    df_ = df.copy()
    df_[[0, 1, 2, 3]] = df_[0].str.split(' ', expand=True)
    for i in range(df_.shape[0]):
        if len(df_.iloc[i, 2]) == 0:
            df_.iloc[i, 2] = df_.iloc[i, 3]
    df_.drop(df_.columns[3], axis=1, inplace=True)
    df = df_.apply(pd.to_numeric, errors='coerce')
    
    x_coord = df.values[:, 0]
    y_coord = df.values[:, 1]
    latitude, longitude = utm.to_latlon(x_coord, y_coord, zone, northern=north_south)
    
    df['lat'] = latitude
    df['lon'] = longitude
    df['bathy'] = np.max(df.iloc[:, 2].values) - df.iloc[:, 2].values
    
    # Plotting
    fig = px.scatter_mapbox(df, lat="lat", lon="lon", color="bathy",
                            color_continuous_scale=px.colors.cyclical.IceFire, size_max=5, zoom=12,
                            mapbox_style="carto-positron")
    
    st.plotly_chart(fig)

#################

# Triangulation
# Renaming columns for easier reference
    df.columns = ['X', 'Y', 'Z']
    northern_hemisphere = True  # Example hemisphere
    
    df['X'], df['Y'] = zip(*df.apply(lambda row: latlon_to_utm(row['Lat'], row['Lon'], utm_zone, northern_hemisphere), axis=1))
    
    points = df[['X', 'Y']].to_numpy()
    tri = Delaunay(points)

    # Function to calculate volume of a triangular prism
    def triangular_prism_volume(p1, p2, p3, h):
        v1 = p2 - p1
        v2 = p3 - p1
        cross_product = np.cross(v1, v2)
        area = np.linalg.norm(cross_product) / 2
        volume = area * h / 3
        return abs(volume)

    # Compute volume
    total_volume = 0
    for simplex in tri.simplices:
        p1, p2, p3 = points[simplex]
        z1, z2, z3 = df.iloc[simplex]['Z']
        avg_depth = (z1 + z2 + z3) / 3
        volume = triangular_prism_volume(p1, p2, p3, avg_depth)
        total_volume += volume
    
    # Show total volume
    st.write("### Total Volume of Water in the Reservoir")
    st.write(total_volume, 'cubic units')

