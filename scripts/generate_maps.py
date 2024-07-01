import geopandas as gpd
import pandas as pd
import os
import fiona
from matplotlib_scalebar.scalebar import ScaleBar
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Define the paths
input_file_path = "./antarctic_index.gpkg"
map_path = "/Users/nathanbekele/Downloads/Quantarctica3/Miscellaneous/SimpleBasemap/ADD_DerivedLowresBasemap.shp"
output_folder = "./data3"
statistics_folder = "./data_statistics"

# Ensure the output folders exist
os.makedirs(output_folder, exist_ok=True)
os.makedirs(statistics_folder, exist_ok=True)

# Read the GeoPackage file into a GeoDataFrame
fp = gpd.read_file(input_file_path)

# Read the map shapefile
mp = gpd.read_file(map_path)

# Check if the 'Category' column exists
if 'Category' in mp.columns:
    # Define the colors for the categories
    category_colors = {
        'Ocean': '#a3bdd1',
        'Ice shelf': '#cfe1eb',
        'Land': '#f0f0f0',
        'Sub-antarctic_G': 'lightgreen',
        'Sub-antarctic_L': 'lightblue',
        'Ice tongue': 'lightgrey',
        'Rumple': 'yellow',
    }

    # Create a color column based on the 'Category' column
    mp['color'] = mp['Category'].map(category_colors).fillna('grey')  # Default to grey for undefined categories

    # Function to plot data on the colored basemap
    def plot_data_on_basemap(basemap, gdf, institution, filename):
        fig, ax = plt.subplots(figsize=(10, 10))

        # Set background color to white
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')

        # Plot basemap with custom colors
        basemap.plot(ax=ax, color=basemap['color'], edgecolor='black')

        # Define colors and labels based on availability
        availability_colors = {'u': '#fb9a99', 's': '#1f78bc', 'o': 'grey'}
        availability_labels = {'u': 'Unavailable', 's': 'Available', 'o': 'Outdated'}

        # Plot the data for the institution
        if not gdf.empty:
            for availability in ['s', 'u', 'o']:  # Ensure the order of plotting
                subset = gdf[gdf['availability'] == availability]
                if not subset.empty:
                    color = availability_colors.get(availability, 'darkgrey')
                    label = availability_labels.get(availability, 'Other')
                    subset.plot(ax=ax, color=color, markersize=0.55, linewidth=0.25, label=label)

        # Set limits to zoom in on Antarctica
        ax.set_xlim(-3e6, 3e6)
        ax.set_ylim(-3e6, 3e6)

        # Set equal aspect ratio for circular plot and remove axes
        ax.set_aspect('equal')
        ax.axis('off')

        # Add custom scale bar with "1000 km" label only
        scalebar = ScaleBar(1, location='lower right', units='km', dimension='si-length', label='1000 km', length_fraction=0.2)
        scalebar.dx = 1  # Set the distance to 1 unit of whatever is specified (km in this case)
        scalebar.label = '1000 km'  # Custom label

        ax.add_artist(scalebar)

        plt.title(f'{institution} Data Availability', fontsize=14)

        # Handle legend
        legend_patches = [Patch(color=color, label=availability_labels[availability]) for availability, color in availability_colors.items()]
        ax.legend(handles=legend_patches, loc='upper right', fontsize=8, title='Availability')

        # Draw a circular boundary
        circle = plt.Circle((0, 0), 3e6, transform=ax.transData, color='black', fill=False, linewidth=1)
        ax.add_artist(circle)

        # Save the plot to the data folder
        output_path = os.path.join(output_folder, filename)
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        print(f"Saved map for {institution} to {output_path}")

    try:
        layers = fiona.listlayers(input_file_path)
        if not layers:
            raise ValueError("No layers found in the GeoPackage.")
        print("Layers in the GeoPackage:")
        print(layers)
    except Exception as e:
        print(f"Error listing layers in the GeoPackage: {e}")
        layers = []

    if not layers:
        print("No layers found or error in listing layers. Exiting.")
    else:
        # Create a dictionary to map institutions to layers
        institution_layers = {}

        # Populate the dictionary
        for layer in layers:
            try:
                gdf = gpd.read_file(input_file_path, layer=layer)  # Read the full layer
                if 'institution' in gdf.columns:
                    institutions = gdf['institution'].unique()
                    for institution in institutions:
                        if institution not in institution_layers:
                            institution_layers[institution] = []
                        institution_layers[institution].append(layer)
            except Exception as e:
                print(f"Error reading layer {layer}: {e}")

        print("Institution layers mapping:")
        print(institution_layers)

        # Create an overview GeoDataFrame
        overview_gdf = gpd.GeoDataFrame()

        # Iterate through each institution and create maps
        for institution, layers in institution_layers.items():
            institution_data = []

            print(f"\nProcessing institution: {institution}")

            for layer in layers:
                print(f"Checking layer: {layer}")
                try:
                    gdf = gpd.read_file(input_file_path, layer=layer)  # Read the full layer

                    if 'institution' in gdf.columns and institution in gdf['institution'].unique():
                        print(f"Layer '{layer}' contains '{institution}'.")
                        institution_data.append(gdf[gdf['institution'] == institution])
                    else:
                        print(f"Layer '{layer}' does not contain '{institution}' or does not have 'institution' column.")
                except Exception as e:
                    print(f"Error processing layer {layer}: {e}")

            # Combine all dataframes for the institution
            if institution_data:
                institution_gdf = gpd.GeoDataFrame(pd.concat(institution_data, ignore_index=True))
            else:
                institution_gdf = gpd.GeoDataFrame()

            # Ensure the CRS matches between the basemap and the GeoDataFrame
            if not institution_gdf.empty:
                institution_gdf = institution_gdf.to_crs(mp.crs)

            # Add to the overview GeoDataFrame
            if not institution_gdf.empty:
                overview_gdf = pd.concat([overview_gdf, institution_gdf])

            # Plot and save the aggregated data for the institution
            plot_data_on_basemap(mp, institution_gdf, institution, f'Antarctica_coverage_{institution}.png')

        # Ensure the CRS matches between the basemap and the overview GeoDataFrame
        if not overview_gdf.empty:
            overview_gdf = gpd.GeoDataFrame(overview_gdf).to_crs(mp.crs)

        # Plot and save the overview map
        plot_data_on_basemap(mp, overview_gdf, "Overview", 'Antarctica_coverage_overview.png')

        print("All maps have been created and saved to the data3 folder.")

else:
    print("The 'Category' column does not exist in the GeoDataFrame.")
