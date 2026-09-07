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
    # Parses command line arguments for start and end dates
    parser = argparse.ArgumentParser(description="Analyze customer orders.")
    parser.add_argument("--start-date", type=pd.to_datetime, required=True)
    parser.add_argument("--end-date", type=pd.to_datetime, required=True)
    return parser.parse_args()

def filter_orders_by_date(orders, start_date, end_date):
    # Filters orders to only include those within the given date range (inclusive).
    mask = (orders['date'] >= start_date) & (orders['date'] <= end_date)
    return orders.loc[mask].copy()

def aggregate_by_customer(orders_with_customers):
    # Aggregates the orders by customer:  total spent and number of orders in the filtered period
    agg = orders_with_customers.groupby(
        ['customer_id', 'name', 'tier'], as_index=False
    ).agg(
        total_spent=('value', 'sum'),
        order_count=('order_id', 'count'),
    )
    return agg

def apply_discount_rules(row):
    # Applies business rules for discount eligibility
    if row['order_count'] < 2:
        return 0.0
    if row['tier'] == 'VIP':
        return 0.10
    if row['tier'] == 'Regular' and row['total_spent'] > 500:
        return 0.05
    return 0.0

def apply_discounts(merged_agg_df):
    # Applies discount rules to the aggregated DataFrame and calculates total after discount
    customer_agg = merged_agg_df.copy()
    customer_agg['discount_pct'] = customer_agg.apply(apply_discount_rules, axis=1)
    customer_agg['total_after_discount'] = (
        customer_agg['total_spent'] * (1 - customer_agg['discount_pct'])
    )
    return customer_agg

def flag_suspicious_orders(orders):
    # Flags orders whose value is more than 3x the customer's average order value
    orders = orders.copy()
    customer_avg = orders.groupby('customer_id')['value'].transform('mean')
    orders['is_suspicious'] = orders['value'] > (3 * customer_avg)
    return orders

def get_suspicious_orders_by_customer(orders):
    # Returns a dict mapping customer_id -> list of suspicious order records
    suspicious = orders[orders['is_suspicious']]
    result = {}
    for customer_id, group in suspicious.groupby('customer_id'):
        result[customer_id] = group[['order_id', 'value', 'date']].to_dict('records')
    return result

def main():
    args = parse_arguments()
    orders = read_csv(orders_path)
    customers = read_json(customers_path)

    orders = prepare_orders_dataframe(orders)
    orders = filter_orders_by_date(orders, args.start_date, args.end_date)
    orders = flag_suspicious_orders(orders)

    orders_with_customers = merge_dataframes(orders, customers)
    customer_summary = aggregate_by_customer(orders_with_customers)
    customer_summary = apply_discounts(customer_summary)

    print(customer_summary)

if __name__ == "__main__":
    main()