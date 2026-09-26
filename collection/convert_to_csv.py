import pandas as pd

# Load the parquet file
df = pd.read_parquet("aidev_all_commits.parquet")

# (Optional) Show the total number of rows and columns
print("Shape:", df.shape)

# (Optional) View all column names
print("Columns:", df.columns.tolist())

df.to_csv("data_csv/data.csv", index=False)
