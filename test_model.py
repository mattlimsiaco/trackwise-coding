from model import predict_fda_code

# Define test inputs
event_desc = "During routine inspection, a white residue was seen..."
prod_id = "Sterile Surgical Instrument Set - Model X123, Lot #A4792"

# Call the function
result = predict_fda_code(event_desc, prod_id)

# Extract the code and format it
device_code = result.get("code", "Unknown")
print(f"Device Code: {device_code}")
