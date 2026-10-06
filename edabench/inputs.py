import re
from pathlib import Path

import openpyxl
import yaml


def repositories(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows, seen = [], set()
    try:
        for sheet in workbook:
            iterator = iter(sheet.values)
            header = next(iterator, ())
            if 'full_name' not in header:
                continue
            col = header.index('full_name')
            for number, row in enumerate(iterator, 2):
                name = row[col]
                if name is None:
                    continue
                name = str(name).strip()
                if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name):
                    raise ValueError(f'Invalid repository at {sheet.title}:{number}')
                rows.append({'full_name': name, 'sheet': sheet.title, 'row': number,
                             'duplicate': name.lower() in seen})
                seen.add(name.lower())
    finally:
        workbook.close()
    if not rows:
        raise ValueError('Excel has no full_name repository rows')
    return rows


def token(path):
    data = yaml.safe_load(Path(path).read_text())
    values = data.get('github_token')
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list) or not values or not isinstance(values[0], str) or not values[0].strip():
        raise ValueError('Expected a nonempty github_token string or list')
    return values[0].strip()
