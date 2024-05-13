# Run this on a different x64 / arm64 machine as the egg needs to compile
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt

def create_mercator_map(filename, width, height, latrange_min, latrange_max):
    # Create a figure and an axes with the specified pixel dimensions
    # Avoid polar regions using latrange_min and latrange_max, also helps
    # to achieve the best resolution possible with regard to aspect ratio
    fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])

    # Set up the Basemap with adjusted latitude range
    m = Basemap(projection='merc', llcrnrlat=latrange_min, urcrnrlat=latrange_max,
                llcrnrlon=-180, urcrnrlon=180, resolution='c', ax=ax)
    m.drawmapboundary(fill_color='black')
    m.fillcontinents(color=(0.25, 0.25, 0.25), lake_color='black')

    # Save the figure without white borders
    plt.savefig(filename, format='png', transparent=False, bbox_inches='tight', pad_inches=0, dpi=100)

create_mercator_map('map476320.png', 480, 320, -63, 83)
create_mercator_map('map800477.png', 800, 480, -60, 80)
