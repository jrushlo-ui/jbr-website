#!/usr/bin/env python3
"""Convert displayed values from the Queue worksheet into release inputs."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys


HEADERS = ['Date', 'Status', 'Article', 'Topic', 'Slug', 'Description',
           'Image', 'Label', 'Published on', 'Live URL']
FIELDS = {'date': 'Date', 'slug': 'Slug', 'title': 'Article', 'description': 'Description',
          'topic': 'Topic', 'image': 'Image', 'label': 'Label'}


def ready_entries(values):
    if not values or values[0] != HEADERS:
        raise ValueError('Expected the ten named columns from the Queue worksheet, A:J')
    entries = []
    seen = set()
    for number, cells in enumerate(values[1:], 2):
        if not any(str(cell).strip() for cell in cells):
            continue
        row = dict(zip(HEADERS, list(cells) + [''] * len(HEADERS)))
        status = str(row['Status']).strip()
        slug = str(row['Slug']).strip()
        if status == 'Hold':
            continue
        if status not in {'Ready', 'Published'}:
            raise ValueError(f'Queue row {number} needs Ready, Hold, or Published in Status')
        if not slug or slug in seen:
            raise ValueError(f'Missing or duplicate active slug on row {number}: {slug!r}')
        seen.add(slug)
        if status == 'Published':
            continue
        entry = {key: str(row[column]).strip() for key, column in FIELDS.items()}
        try:
            scheduled = date.fromisoformat(entry['date'])
        except ValueError as exc:
            raise ValueError(f'Use a YYYY-MM-DD release date on row {number}') from exc
        if scheduled.isoformat() != entry['date'] or not all(entry.values()):
            raise ValueError(f'Incomplete release information on Ready row {number}')
        entries.append(entry)
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('values', type=Path, help='JSON array of cell rows or a Sheets object with values')
    parser.add_argument('output', type=Path, help='Write queue.json next to the publisher in its temporary checkout')
    args = parser.parse_args()
    data = json.loads(args.values.read_text(encoding='utf-8'))
    entries = ready_entries(data['values'] if isinstance(data, dict) else data)
    args.output.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        sys.exit(str(exc))
