from pathlib import Path
import pandas as pd
import argparse

BASE_DIR = Path(__file__).resolve().parent.parent / "data"
orders_path = BASE_DIR / "orders.csv"
customers_path = BASE_DIR / "customers.json"

def read_csv(file_path):
    # Reads a CSV file and return a DataFrame
    return pd.read_csv(file_path)

def read_json(file_path):
    # Reads a JSON file and returns a Dataframe
    return pd.read_json(file_path)

def prepare_orders_dataframe(orders):
    # Prepares the orders DataFrame by renaming columns, converting date to datetime, and ensuring value is numeric
    orders = orders.rename(columns={'id': 'order_id'})
    orders['date'] = pd.to_datetime(orders['date'])
    orders['value'] = pd.to_numeric(orders['value'], errors='raise')
    return orders

def merge_dataframes(orders, customers):
    # Merges the orders and customers DataFrames on the customer_id and id columns
    return orders.merge(
        customers,
        how='left',
        left_on='customer_id',
        right_on='id',
        validate='many_to_one').drop(columns='id')

def parse_arguments():
    parser = argparse.ArgumentParser(description="Analyze customer orders.")
    parser.add_argument("--start-date", type=pd.to_datetime, required=True)
    parser.add_argument("--end-date", type=pd.to_datetime, required=True)
    return parser.parse_args()

def main():
    args = parse_arguments()

    orders = read_csv(orders_path)
    customers = read_json(customers_path)

    orders = prepare_orders_dataframe(orders)

    orders_with_customers = merge_dataframes(orders, customers)



if __name__ == "__main__":
    main()