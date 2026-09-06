from pathlib import Path
import pandas as pd
import json

BASE_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = BASE_DIR / "data"

orders_path = BASE_DIR / "orders.csv"
customers_path = BASE_DIR / "customers.json"

def read_csv(csv_file):
    # Reads a CSV file and return a DataFrame
    return pd.read_csv(csv_file)

def read_json(json_file):
    # Reads a JSON file and returns a Dataframe
    with open(json_file, 'r', encoding='utf-8') as file:
        json_data = json.load(file)
    return pd.DataFrame(json_data)

def merge_dataframes(orders, customers):
    # Merges the orders and customers DataFrames on the customer_id and id columns
    orders = read_csv(orders).rename(columns={'id': 'order_id'})
    orders['date'] = pd.to_datetime(orders['date'])
    if not pd.api.types.is_numeric_dtype(orders['value']):
        orders['value'] = pd.to_numeric(orders['value'], errors='raise')
    return orders.merge(
        read_json(customers),
        how='left',
        left_on='customer_id',
        right_on='id',
        validate='many_to_one').drop(columns='id')

def main():

    customers_orders = merge_dataframes(orders_path, customers_path)
    print(customers_orders.head())

if __name__ == "__main__":
    main()