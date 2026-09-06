# CloudWalk — Collection Engineer Technical Challenge

Python solution for the **Collection Engineer technical challenge**, focused on analyzing customer orders, applying business rules, detecting potentially suspicious orders, and generating a consolidated customer report.

## Overview

The application processes two input datasets:

* `customers.json` — customer information, including identifier, name, and category.
* `orders.csv` — order information, including identifier, customer identifier, value, and order date.

The solution:

1. Loads and consolidates customer and order data using `customer_id`.
2. Filters orders by a user-defined date interval.
3. Calculates the total amount spent by each customer.
4. Applies the required discount rules.
5. Identifies potentially suspicious orders.
6. Generates a consolidated final report.

## Business Rules

### Discounts

* **VIP customers:** 10% discount on total spending.
* **Regular customers:** 5% discount when total spending is above **R$500**.
* A discount is only applied when the customer has made **at least 2 orders** during the analyzed period.

### Suspicious Orders

An order is marked as `suspeito` when its value is greater than **3 times the customer's average order value**.

## Project Structure

```text
collection-challenge/
│
├── data/
│   ├── customers.json
│   └── orders.csv
│
├── src/
│   └── main.py
│
├── tests/
│   └── test_main.py
│
├── README.md
├── requirements.txt
└── .gitignore
```

## Requirements

* Python 3.10+
* pip

## Installation

Clone the repository and create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## Input Data

The input datasets are intentionally not included in the repository due to data privacy considerations.

Place the provided files in the following directory:

```text
data/
├── customers.json
└── orders.csv
```

## Usage

The application accepts a start and end date to define the analysis period.

Example:

```bash
python src/main.py --start-date 2026-01-01 --end-date 2026-03-31
```

Only orders within the specified period are considered when calculating totals, discounts, order counts, and suspicious orders.

## Tests

Run the test suite with:

```bash
pytest
```

The tests cover the main business rules and data analysis logic.

## AI / LLM Usage

AI/LLM tools were used as development assistants throughout the implementation.

They were used for activities such as:

* discussing solution architecture;
* reviewing implementation approaches;
* identifying edge cases;
* suggesting test scenarios;
* reviewing code quality and readability;
* improving documentation.

The AI was not used as a substitute for understanding or validating the business requirements. The final implementation and decisions were reviewed and validated manually.

**No customer or order data was submitted to external LLM services.** Prompts involving the business logic were kept data-agnostic to avoid exposing potentially sensitive information.

## Technical Decisions

The implementation prioritizes:

* readability;
* simple and maintainable Python code;
* separation of data loading, business rules, and reporting logic;
* reproducible execution through command-line arguments;
* automated tests for the core business rules.

The solution intentionally avoids unnecessary infrastructure or dependencies because the challenge is focused on data processing and business logic rather than deployment.

## Notes

The suspicious-order rule is applied according to the challenge specification: an order is considered suspicious when its value is greater than three times the customer's average order value within the analyzed period.
