# CloudWalk — Collection Engineer Technical Challenge

Python solution for the **Collection Engineer technical challenge**, focused on analyzing customer orders, applying business rules, detecting potentially suspicious orders, and generating a consolidated customer report.

## Overview

The application processes two input datasets:

* `customers.json` — customer information, including identifier, name, and tier.
* `orders.csv` — order information, including identifier, customer identifier, value, and order date.

The solution:

1. Loads and consolidates customer and order data using `customer_id`.
2. Filters orders by a user-defined date interval.
3. Calculates the total amount spent by each customer within that period.
4. Applies the required discount rules.
5. Identifies potentially suspicious orders.
6. Generates a consolidated final report, printed to the console and exported as JSON.

## Business Rules

### Discounts

* **VIP customers:** 10% discount on total spending.
* **Regular customers:** 5% discount when total spending is above **R$500**.
* A discount is only applied when the customer has made **at least 2 orders** during the analyzed period.

### Suspicious Orders

An order is flagged as suspicious (`is_suspicious`) when its value is greater than **3 times the customer's average order value**, calculated over the orders within the analyzed period.

## Key Interpretation Decisions

The challenge description leaves a few points open to interpretation. The decisions below were made deliberately and are documented here for review:

* **"Above R$500" is treated as strictly greater than (`>`), not `>=`.** A customer with exactly R$500.00 in total spending does not qualify for the Regular discount under this reading.
* **The suspicious-order average includes the order being evaluated.** An alternative reading would exclude the order itself from its own average (a stricter outlier definition), but the literal wording of the spec — "3 times the average of that customer's orders" — was followed as-is.
* **All totals, order counts, and averages are computed only on orders within the `--start-date`/`--end-date` window**, not on the customer's full order history. This applies consistently to discount eligibility (order count ≥ 2) and suspicious-order detection.
* **Orders whose `customer_id` has no match in `customers.json` are excluded from the final report**, with a warning printed to the console (`orders_with_customers` rows with a missing name are dropped during aggregation). This was chosen over silently including them with an unknown tier, since discount rules depend on tier.
* **The report field is named `category`** (matching the challenge wording) even though the internal DataFrame column is named `tier`. This is a deliberate distinction between an internal implementation name and the external report contract.

## Project Structure

```text
collection-challenge/
│
├── data/
│   ├── customers.json
│   └── orders.csv
│
├── output/
│   └── report.json          # generated on each run (git-ignored)
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

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
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

The application requires a start and end date to define the analysis period. Both are validated to ensure `--start-date` does not come after `--end-date`.

Example:

```bash
python src/main.py --start-date 2025-01-01 --end-date 2025-03-31
```

Only orders within the specified period (inclusive) are considered when calculating totals, discounts, order counts, and suspicious orders.

The final report is printed as a summary to the console and written to `output/report.json`.

## Tests

Run the test suite with:

```bash
pytest
```

The tests cover the main business rules and data analysis logic, including:

* discount eligibility and percentage calculation per tier;
* the minimum order-count requirement for discount eligibility;
* suspicious-order detection;
* date-range filtering behavior;
* report structure and field naming.

## AI / LLM Usage

AI/LLM tools were used as development assistants throughout the implementation.

They were used for activities such as:

* discussing solution architecture and module structure;
* reviewing implementation approaches and debugging errors;
* identifying edge cases and ambiguities in the business rules;
* suggesting test scenarios;
* reviewing code quality and readability;
* improving documentation.

The AI was not used as a substitute for understanding or validating the business requirements. All business rule interpretations, architectural decisions, and the final implementation were reviewed and validated manually — see [Key Interpretation Decisions](#key-interpretation-decisions) above.

**No customer or order data was submitted to external LLM services.** Prompts involving the business logic were kept data-agnostic to avoid exposing potentially sensitive information.

## Technical Decisions

The implementation prioritizes:

* readability and explicitness over premature optimization (e.g. `apply()` for discount rules instead of a vectorized `np.select`, favoring clarity for a small dataset);
* simple and maintainable Python code;
* separation of data loading, business rules, and reporting logic into small, single-purpose functions;
* reproducible execution through command-line arguments, with input validation (date range order) failing fast with a clear CLI error message;
* explicit handling of unmatched/orphan records rather than allowing them to fail silently;
* automated tests for the core business rules.

The solution intentionally avoids unnecessary infrastructure or dependencies (no database, no web framework, no orchestration) because the challenge is focused on data processing and business logic rather than deployment.

## Notes

The suspicious-order rule and the discount rules are applied according to the challenge specification, with the interpretation choices documented in [Key Interpretation Decisions](#key-interpretation-decisions). Where the spec was ambiguous, the decision that most closely matched a literal reading of the requirements was chosen, and alternatives were noted for discussion.