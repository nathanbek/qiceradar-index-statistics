import geopandas as gpd
import pandas as pd
import os
from shapely.geometry import MultiPoint, LineString, Point
import fiona

# Define the paths to the input and output files
input_file_path = "./antarctic_index.gpkg"
map_path = "/Users/nathanbekele/Downloads/Quantarctica3/Miscellaneous/SimpleBasemap/ADD_DerivedLowresBasemap.shp"
output_folder = "./data3"
statistics_folder = "./data_statistics"

# Ensure the output folders exist
os.makedirs(output_folder, exist_ok=True)
os.makedirs(statistics_folder, exist_ok=True)

# Function to calculate distance from geometries
def calculate_distance(geometry):
    if isinstance(geometry, MultiPoint):
        points = [point for point in geometry.geoms]
        line = LineString(points)
        return round(line.length / 1000)  # Convert meters to kilometers and round to the nearest km
    elif isinstance(geometry, LineString):
        return round(geometry.length / 1000)  # Convert meters to kilometers and round to the nearest km
    elif isinstance(geometry, Point):
        return 0  # A single point has no length
    else:
        return 0  # Handle other geometry types accordingly

# Function to determine availability status
def determine_availability(row):
    if row['availability'] == 's':
        return 'yes'
    elif row['availability'] == 'u':
        return 'no'
    else:
        return 'outdated'

# Function to format large numbers with commas
def format_with_commas(number):
    return "{:,}".format(number)

# List all layers in the GeoPackage
layers = fiona.listlayers(input_file_path)
all_statistics = []

# Process each layer in the GeoPackage
institution_summary = {}
for layer in layers:
    try:
        gdf = gpd.read_file(input_file_path, layer=layer)
    except Exception as e:
        print(f"Skipping layer {layer} due to read error: {e}")
        continue

    if 'institution' not in gdf.columns:
        print(f"Skipping layer {layer} as it does not contain 'institution' column.")
        continue

    print(f"Processing layer: {layer}")

    # Ensure the CRS is set to EPSG:3031 if not already set
    if gdf.crs is None:
        gdf.set_crs("EPSG:3031", inplace=True)

    # Ensure the CRS is Antarctic Polar Stereographic and convert distances
    if gdf.crs != "EPSG:3031":
        gdf = gdf.to_crs("EPSG:3031")

    # Calculate distances for each row
    gdf['total_distance_km'] = gdf['geometry'].apply(calculate_distance)

    # Calculate available distance based on availability status
    if 'availability' in gdf.columns:
        gdf['available_distance_km'] = gdf.apply(
            lambda row: calculate_distance(row['geometry']) if row['availability'] == 's' else 0, axis=1
        )
        gdf['availability'] = gdf.apply(determine_availability, axis=1)
    else:
        gdf['available_distance_km'] = 0
        gdf['availability'] = 'outdated'

    # Ensure 'campaign' column exists, adding it with default value 'Unknown' if missing
    if 'campaign' not in gdf.columns:
        gdf['campaign'] = 'Unknown'

    # Group by institution and campaign to calculate statistics
    grouped = gdf.groupby(['institution', 'campaign']).agg({
        'total_distance_km': 'sum',
        'available_distance_km': 'sum'
    }).reset_index()

    # Process each institution in the grouped data
    for institution, institution_data in grouped.groupby('institution'):
        if institution not in institution_summary:
            institution_summary[institution] = []

        institution_summary[institution].append(institution_data)

        # Prepare the DataFrame for institution CSV
        institution_df = pd.concat(institution_summary[institution], ignore_index=True)
        institution_total = institution_df.agg({
            'total_distance_km': 'sum',
            'available_distance_km': 'sum'
        }).to_frame().T
        institution_total['campaign'] = 'Total'
        institution_total['institution'] = institution
        institution_total['availability'] = 'N/A'  # Availability does not apply to the total row
        institution_df = pd.concat([institution_df, institution_total], ignore_index=True)

        # Format the distances with commas for readability
        institution_df['total_distance_km'] = institution_df['total_distance_km'].apply(format_with_commas)
        institution_df['available_distance_km'] = institution_df['available_distance_km'].apply(format_with_commas)

        # Save each institution's data to a CSV
        institution_output_path = os.path.join(statistics_folder, f'statistics_{institution}.csv')
        institution_df.to_csv(institution_output_path, index=False)
        print(f"Saved statistics for {institution} to {institution_output_path}")

    # Append the statistics to the all_statistics list for overall summary
    all_statistics.append(grouped)

# Combine all statistics into a single DataFrame for the overview
all_statistics_df = pd.concat(all_statistics, ignore_index=True)

# Group by institution to sum totals for the overview
overview_df = all_statistics_df.groupby('institution').agg({
    'total_distance_km': 'sum',
    'available_distance_km': 'sum'
}).reset_index()

# Format the distances with commas for readability
overview_df['total_distance_km'] = overview_df['total_distance_km'].apply(format_with_commas)
overview_df['available_distance_km'] = overview_df['available_distance_km'].apply(format_with_commas)

# Save the overview statistics to a CSV
overview_output_path = os.path.join(statistics_folder, 'institution_overview.csv')
overview_df.to_csv(overview_output_path, index=False)
print(f"Saved institution overview statistics to {overview_output_path}")

# Display the overview statistics
print("\nInstitution Overview Statistics:")
print(overview_df)

# Display the complete statistics table
print("\nComplete statistics table:")
print(all_statistics_df)
