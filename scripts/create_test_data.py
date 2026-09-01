import json
from pathlib import Path

import pandas as pd


def generate_test_transactions():
    script_dir = Path(__file__).parent
    data_path = script_dir / 'test_transactions.json'

    with data_path.open(encoding='utf-8') as f:
        transactions = json.load(f)

    df = pd.DataFrame(transactions)
    return df


if __name__ == '__main__':
    df = generate_test_transactions()
    output_path = Path(__file__).parent.parent / 'data' / 'test_transactions.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f'Test data saved to {output_path}')
