#!/usr/bin/env python3
import argparse
import json
import os
import sys
from collections import Counter

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import _parse_topic_import_file


def build_summary(rows):
    soft_counter = Counter()
    type_counter = Counter()
    link_count = 0
    for row in rows:
        soft_counter[(row.get('soft_insertion') or '未标记').strip() or '未标记'] += 1
        type_counter[(row.get('content_type') or '未分类').strip() or '未分类'] += 1
        if (row.get('reference_link') or '').strip():
            link_count += 1
    return {
        'count': len(rows),
        'with_reference_links': link_count,
        'soft_insertion': dict(soft_counter),
        'content_types_top10': type_counter.most_common(10),
    }


def main():
    parser = argparse.ArgumentParser(description='Export topic import payload JSON from workbook/csv/text.')
    parser.add_argument('input_path', help='Path to xlsx/csv/txt source file')
    parser.add_argument('-o', '--output', required=True, help='Output JSON path')
    args = parser.parse_args()

    input_path = os.path.abspath(args.input_path)
    output_path = os.path.abspath(args.output)
    with open(input_path, 'rb') as f:
        rows = _parse_topic_import_file(os.path.basename(input_path), f.read())

    payload = {
        'items': rows,
        'summary': build_summary(rows),
        'source_file': input_path,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        'success': True,
        'output_path': output_path,
        'summary': payload['summary'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
