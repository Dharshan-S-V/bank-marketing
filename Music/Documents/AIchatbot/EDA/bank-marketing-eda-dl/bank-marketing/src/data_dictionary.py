"""Data dictionary for bank-full.csv (field descriptions follow the UCI documentation, dataset id 222)."""
import pandas as pd

from .config import DATA_DIR

ROWS = [
    ("age", "numeric (int)", "Age of the client in years", "18-95"),
    ("job", "categorical", "Type of job (12 levels incl. 'unknown')", "admin., blue-collar, management, technician, ..."),
    ("marital", "categorical", "Marital status ('divorced' includes widowed)", "married, single, divorced"),
    ("education", "categorical", "Education level (incl. 'unknown')", "primary, secondary, tertiary, unknown"),
    ("default", "binary", "Has credit in default?", "yes / no"),
    ("balance", "numeric (int)", "Average yearly balance in euros (negative = overdrawn)", "-8,019 to 102,127"),
    ("housing", "binary", "Has a housing loan?", "yes / no"),
    ("loan", "binary", "Has a personal loan?", "yes / no"),
    ("contact", "categorical", "Contact communication type (incl. 'unknown')", "cellular, telephone, unknown"),
    ("day", "numeric (int)", "Day of the month of the last contact", "1-31"),
    ("month", "categorical", "Month of the last contact", "jan ... dec"),
    ("duration", "numeric (int)", "Duration of the last contact in seconds (known only AFTER the call -> excluded from the primary model)", "0-4,918"),
    ("campaign", "numeric (int)", "Number of contacts performed during this campaign for this client (includes the last contact)", "1-63"),
    ("pdays", "numeric (int)", "Days since the client was last contacted in a previous campaign (-1 = never contacted)", "-1, 1-871"),
    ("previous", "numeric (int)", "Number of contacts performed before this campaign for this client", "0-275"),
    ("poutcome", "categorical", "Outcome of the previous marketing campaign (incl. 'unknown')", "success, failure, other, unknown"),
    ("y", "binary (TARGET)", "Did the client subscribe to a term deposit?", "yes / no"),
]


def data_dictionary() -> pd.DataFrame:
    return pd.DataFrame(ROWS, columns=["field", "type", "description", "values / range"])


if __name__ == "__main__":
    d = data_dictionary(); d.to_csv(DATA_DIR / "data_dictionary.csv", index=False); print(d)
