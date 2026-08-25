import pandas as pd
import random

# Generate 50 fake dealer locations across Maharashtra
data = {
    "Dealer_ID": [f"DLR-{1000 + i}" for i in range(50)],
    "Dealer_Name": [f"Auto Service {i}" for i in range(50)],
    "Latitude": [random.uniform(18.0, 20.0) for _ in range(50)],   
    "Longitude": [random.uniform(73.0, 75.0) for _ in range(50)], 
    "MX_Engine_Parts_Stock": [random.randint(0, 50) for _ in range(50)],
    "GHG_Labels_Compliant": [random.choice(['Yes', 'No']) for _ in range(50)]
}

df = pd.DataFrame(data)
df.to_csv("raw_dealer_data.csv", index=False)
print("Mock data generated successfully: raw_dealer_data.csv")