import pandas as pd
from geopy.distance import geodesic

# 1. Define the Central Distribution Hub (Using Pune coordinates)
PUNE_HUB_COORDS = (18.5204, 73.8567)

# 2. Load the raw data you just generated
print("Loading raw dealer data...")
df = pd.read_csv("raw_dealer_data.csv")

# 3. Clean and Filter Data (Identify dealers with critically low MX Engine parts)
CRITICAL_STOCK_LEVEL = 10
low_stock_dealers = df[df['MX_Engine_Parts_Stock'] < CRITICAL_STOCK_LEVEL].copy()

# 4. Automate Distance Mapping
# We want to know exactly how far the delivery truck needs to go for each low-stock dealer
def calculate_distance(row):
    dealer_coords = (row['Latitude'], row['Longitude'])
    # Returns distance in kilometers
    return round(geodesic(PUNE_HUB_COORDS, dealer_coords).kilometers, 2)

print("Calculating delivery distances for critical dealers...")
low_stock_dealers['Distance_from_Hub_km'] = low_stock_dealers.apply(calculate_distance, axis=1)

# 5. Sort by distance to optimize the delivery route
optimized_route = low_stock_dealers.sort_values(by='Distance_from_Hub_km')

# 6. Export an Automated Excel Report (This is the "800 man-hours" saved)
output_file = "Automated_Dispatch_Report.xlsx"
optimized_route.to_excel(output_file, index=False)
print(f"Success! Automated report generated: {output_file}")