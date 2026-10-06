"""Offline PR-level aggregation and deterministic candidate-pool statistics."""
import argparse
from collections import Counter, defaultdict
import csv
import io
import json
import os
from pathlib import Path
from statistics import mean, median
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.assemble_thread_annotations import _atomic_json, _atomic_jsonl, _atomic_text, _sha256


SCHEMA_VERSION = 'eda-pr-candidates-v1'
LOCATION_FIELDS = ('path', 'side', 'from_line', 'to_line')
LOC_BINS = ((0, '0'), (50, '1-50'), (200, '51-200'), (500, '201-500'),
            (1000, '501-1000'), (float('inf'), '1001+'))
ISSUE_BINS = ((0, '0'), (1, '1'), (5, '2-5'), (10, '6-10'),
              (20, '11-20'), (float('inf'), '21+'))


def jsonl(path):
    with path.open(encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def unique_index(rows, key):
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ValueError(f'duplicate {key}: {value}')
        result[value] = row
    return result


def aggregate(samples, assessments, repairs=None):
    assessments = unique_index(assessments, 'thread_key')
    repairs = repairs or {}
    seen_prs, seen_threads, rows = set(), set(), []
    for sample in sorted(samples, key=lambda s: (s['metadata']['repository'], s['metadata']['number'],
                                                s['source_commit'], s['target_commit'])):
        meta = sample['metadata']
        identity = (meta['repository'], meta['number'], sample['source_commit'], sample['target_commit'])
        if identity in seen_prs:
            raise ValueError(f'duplicate PR revision: {identity}')
        seen_prs.add(identity)
        grouped = defaultdict(list)
        for comment in sample['comments']:
            grouped[comment['metadata']['thread_root_id']].append(comment)
        threads = []
        for root_id, comments in sorted(grouped.items()):
            key = f"{meta['repository']}#{meta['number']}:{root_id}"
            if key in seen_threads or key not in assessments:
                raise ValueError(f'duplicate or missing assessment: {key}')
            seen_threads.add(key)
            assessment = assessments[key]
            anchor = {field: comments[0][field] for field in LOCATION_FIELDS}
            location = comments[0]['metadata']['location_status']
            if assessment['provenance']['location_status'] != location:
                raise ValueError(f'location status mismatch: {key}')
            issues = []
            for index, issue in enumerate(assessment['issues'], 1):
                if any(issue[field] != anchor[field] for field in LOCATION_FIELDS):
                    raise ValueError(f'issue anchor mismatch: {key}')
                issues.append({**issue, 'issue_id': f'{key}/issue/{index}', 'location_status': location})
            thread = {**assessment, 'thread_root_id': root_id,
                      'original_comment_ids': [c['metadata']['comment_id'] for c in comments],
                      'anchor': {**anchor, 'location_status': location}, 'issues': issues}
            if key in repairs:
                thread['annotation_repair'] = repairs[key]
            threads.append(thread)
        decisions = Counter(t['decision'] for t in threads)
        issue_count = sum(len(t['issues']) for t in threads)
        located_count = sum(len(t['issues']) for t in threads if t['anchor']['location_status'] == 'verified')
        rows.append({
            'pr_key': f"{meta['repository']}#{meta['number']}@{sample['source_commit']}..{sample['target_commit']}",
            'repository': meta['repository'], 'number': meta['number'],
            'githubPrUrl': sample['githubPrUrl'], 'source_commit': sample['source_commit'],
            'target_commit': sample['target_commit'], 'title': meta['title'],
            'project_main_language': sample['project_main_language'],
            'closed_at': meta['closed_at'], 'merged_at': meta['merged_at'],
            'statistics': meta['statistics'], 'diff_path': meta['diff_path'], 'diff_sha256': meta['diff_sha256'],
            'original_comment_count': len(sample['comments']), 'thread_count': len(threads),
            'decision_counts': dict(decisions), 'candidate_issue_count': issue_count,
            'located_candidate_issue_count': located_count,
            'unlocated_candidate_issue_count': issue_count - located_count,
            'human_verified': False, 'threads': threads,
        })
    if seen_threads != set(assessments):
        raise ValueError('assessments contain threads absent from source samples')
    return rows


def bucket(value, bins):
    return next(label for limit, label in bins if value <= limit)


def statistics(rows):
    groups = {name: defaultdict(Counter) for name in ('repository', 'project_main_language', 'changed_loc')}
    issue_groups = {name: defaultdict(Counter) for name in ('file_extension', 'category')}
    issue_prs = defaultdict(set)
    total = Counter()
    histograms = {name: Counter() for name in ('candidate_issue_count', 'located_candidate_issue_count')}
    for row in rows:
        counts = {'pr_count': 1, 'candidate_pr_count': int(row['candidate_issue_count'] > 0),
                  'located_candidate_pr_count': int(row['located_candidate_issue_count'] > 0),
                  'thread_count': row['thread_count'], 'comment_count': row['original_comment_count'],
                  'candidate_issue_count': row['candidate_issue_count'],
                  'located_candidate_issue_count': row['located_candidate_issue_count'],
                  'unlocated_candidate_issue_count': row['unlocated_candidate_issue_count']}
        total.update(counts)
        for name, value in [('repository', row['repository']),
                            ('project_main_language', row['project_main_language'] or '(unknown)'),
                            ('changed_loc', bucket(row['statistics']['changed_loc'], LOC_BINS))]:
            groups[name][value].update(counts)
        for name in histograms:
            histograms[name][row[name]] += 1
        for thread in row['threads']:
            for item in thread['issues']:
                extension = Path(item['path']).suffix.lower() if item['path'] else '(unknown)'
                for name, value in [('file_extension', extension or '(no extension)'), ('category', item['category'])]:
                    group = issue_groups[name][value]
                    group['candidate_issue_count'] += 1
                    group['located_candidate_issue_count'] += int(item['location_status'] == 'verified')
                    group['unlocated_candidate_issue_count'] += int(item['location_status'] != 'verified')
                    issue_prs[(name, value, 'all')].add(row['pr_key'])
                    if item['location_status'] == 'verified':
                        issue_prs[(name, value, 'located')].add(row['pr_key'])
    distributions = {name: {key: dict(value) for key, value in sorted(group.items())}
                     for name, group in groups.items()}
    for name, group in issue_groups.items():
        distributions[name] = {value: {**counts, 'candidate_pr_count': len(issue_prs[(name, value, 'all')]),
                                       'located_candidate_pr_count': len(issue_prs[(name, value, 'located')])}
                               for value, counts in sorted(group.items())}
    numeric = {}
    for name, values in [('changed_loc', [r['statistics']['changed_loc'] for r in rows]),
                         ('changed_files', [r['statistics']['changed_files'] for r in rows]),
                         ('hunks', [r['statistics']['hunks'] for r in rows]),
                         *[(name, [r[name] for r in rows]) for name in histograms]]:
        numeric[name] = {'min': min(values), 'median': median(values), 'mean': mean(values), 'max': max(values)}
    return {'schema_version': SCHEMA_VERSION, 'human_verified': False, 'totals': dict(total),
            'decision_counts': dict(sum((Counter(r['decision_counts']) for r in rows), Counter())),
            'distributions': distributions, 'numeric_summaries_all_prs': numeric,
            'issues_per_pr': {name: {'exact': dict(sorted(hist.items())),
                                     'binned': dict(sum((Counter({bucket(n, ISSUE_BINS): count})
                                                        for n, count in hist.items()), Counter()))}
                              for name, hist in histograms.items()}}


def markdown_report(stats):
    t = stats['totals']
    lines = ['# PR 级候选池统计', '',
             f"覆盖 {t['pr_count']:,} 个已导出 PR、{t['thread_count']:,} 个线程、{t['comment_count']:,} 条原始评论。",
             f"有候选意见的 PR：{t['candidate_pr_count']:,}；有可定位候选意见的 PR：{t['located_candidate_pr_count']:,}。",
             f"候选意见 {t['candidate_issue_count']:,} 条，其中可定位 {t['located_candidate_issue_count']:,} 条、未定位 {t['unlocated_candidate_issue_count']:,} 条。", '',
             '类别沿用模型候选标签，不代表已确认缺陷。统计包含零候选 PR，不做筛选、抽样或语义去重。',
             '变更规模来自选定 source→target。文件后缀来自候选意见位置，不是 PR 全部变更文件，也不是仓库主语言。',
             '多文件类型/多类别的 PR 可在多个分组出现，相应 PR 数不能跨组相加；意见条数可以相加。',
             '原始采集存在失败任务，本报告只覆盖已导出的语料，不代表全部 GitHub PR。', '',
             '## 分布', '']
    for name, title in [('repository', '仓库'), ('project_main_language', '仓库主语言'),
                        ('file_extension', '候选所在文件后缀'), ('category', '候选类别'), ('changed_loc', '选定版本变更 LOC')]:
        lines += [f'### {title}', '', '| 分组 | PR 数 | 有候选 PR | 有可定位候选 PR | 候选意见 | 可定位意见 | 未定位意见 |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        data = stats['distributions'][name]
        keys = ([label for _, label in LOC_BINS if label in data] if name == 'changed_loc' else
                sorted(data, key=lambda k: (-data[k]['candidate_issue_count'], k)))
        for key in keys:
            g = data[key]
            lines.append(f"| {key} | {g.get('pr_count', '—')} | {g['candidate_pr_count']} | {g['located_candidate_pr_count']} | {g['candidate_issue_count']} | {g['located_candidate_issue_count']} | {g['unlocated_candidate_issue_count']} |")
        lines += ['']
    lines += ['## 每 PR 意见数量（包括零候选 PR）', '', '| 意见数 | 全部候选口径 PR 数 | 可定位候选口径 PR 数 |', '|---|---:|---:|']
    for _, label in ISSUE_BINS:
        values = [stats['issues_per_pr'][name]['binned'].get(label, 0)
                  for name in ('candidate_issue_count', 'located_candidate_issue_count')]
        lines.append(f'| {label} | {values[0]} | {values[1]} |')
    lines += ['', '## 数值概况（全部 PR）', '', '| 指标 | 最小 | 中位数 | 平均 | 最大 |', '|---|---:|---:|---:|---:|']
    for name, values in stats['numeric_summaries_all_prs'].items():
        lines.append(f"| {name} | {values['min']} | {values['median']} | {values['mean']:.2f} | {values['max']} |")
    return '\n'.join(lines) + '\n'


def build(data, run_dir, output):
    data, run_dir, output = Path(data), Path(run_dir), Path(output)
    paths = {'samples': data / 'dataset/samples.json', 'source_manifest': data / 'dataset/manifest.json',
             'annotation_manifest': run_dir / 'manifest.json', 'annotation_report': run_dir / 'report.json',
             'assessments': run_dir / 'thread_assessments.jsonl', 'located_issues': run_dir / 'candidate_issues.jsonl'}
    # Keep the repair history referenced by the run, including the actor of semantic corrections.
    execution_path = run_dir / 'execution.json'
    execution = json.loads(execution_path.read_text()) if execution_path.exists() else {}
    repairs = {}
    if execution.get('repair_audit'):
        paths['execution'] = execution_path
        paths['repairs'] = run_dir / execution['repair_audit'] / 'repairs.jsonl'
        repairs = {r['thread_key']: {'kind': r['kind'], 'note': r['note'],
                                    'record_file': os.path.relpath(paths['repairs'], output),
                                    'actor': execution['repair_actor']}
                   for r in jsonl(paths['repairs'])}
    fingerprints = {name: {'path': os.path.relpath(path, output), 'sha256': _sha256(path)}
                    for name, path in paths.items()}
    source = json.loads(paths['source_manifest'].read_text())
    manifest = json.loads(paths['annotation_manifest'].read_text())
    report = json.loads(paths['annotation_report'].read_text())
    if not report.get('classification_complete'):
        raise ValueError('annotation classification is not complete')
    if fingerprints['samples']['sha256'] != source['samples_sha256'] or fingerprints['samples']['sha256'] != manifest['source_samples_sha256']:
        raise ValueError('source samples hash mismatch')
    assessments = jsonl(paths['assessments'])
    tasks = unique_index(manifest['tasks'], 'thread_key')
    if set(tasks) != {a['thread_key'] for a in assessments}:
        raise ValueError('manifest and assessment coverage differ')
    for assessment in assessments:
        task = tasks[assessment['thread_key']]
        if (task['input_sha256'] != assessment['input_sha256'] or
                task['input_file'] != assessment['provenance']['input_file']):
            raise ValueError(f"assessment input mismatch: {assessment['thread_key']}")
    rows = aggregate(json.loads(paths['samples'].read_text()), assessments, repairs)
    stats = statistics(rows)
    counts = stats['totals']
    expected = {'task_count': counts['thread_count'], 'valid_output_count': counts['thread_count'],
                'missing_count': 0, 'invalid_count': 0, 'issue_count': counts['candidate_issue_count'],
                'verified_issue_count': counts['located_candidate_issue_count']}
    if report['total'] != expected or stats['decision_counts'] != report['full']['decision_counts']:
        raise ValueError('annotation report counts differ from assessments')
    def signature(key, url, source_sha, target_sha, issue):
        return json.dumps([key, url, source_sha, target_sha, issue], sort_keys=True, ensure_ascii=False)
    actual = Counter(signature(r['thread_key'], r['githubPrUrl'], r['source_commit'], r['target_commit'], r['issue'])
                     for r in jsonl(paths['located_issues']))
    reconstructed = Counter(signature(t['thread_key'], r['githubPrUrl'], r['source_commit'], r['target_commit'],
                                      {k: v for k, v in i.items() if k not in ('issue_id', 'location_status')})
                            for r in rows for t in r['threads'] for i in t['issues'] if i['location_status'] == 'verified')
    if actual != reconstructed:
        raise ValueError('located candidate content or PR revision mismatch')
    fields = ('pr_key', 'repository', 'number', 'githubPrUrl', 'source_commit', 'target_commit',
              'project_main_language', 'original_comment_count', 'thread_count', 'candidate_issue_count',
              'located_candidate_issue_count', 'unlocated_candidate_issue_count', 'changed_loc', 'changed_files', 'hunks')
    csv_text = io.StringIO()
    writer = csv.DictWriter(csv_text, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows({k: r[k] if k in r else r['statistics'][k] for k in fields} for r in rows)
    # Detect changing sources before publishing a derived snapshot.
    if any(_sha256(path) != fingerprints[name]['sha256'] for name, path in paths.items()):
        raise ValueError('source files changed during aggregation')
    _atomic_jsonl(output / 'pr_candidates.jsonl', rows)
    _atomic_text(output / 'pr_summary.csv', csv_text.getvalue())
    _atomic_json(output / 'statistics.json', stats)
    _atomic_text(output / 'report.md', markdown_report(stats))
    _atomic_json(output / 'manifest.json', {
        'schema_version': SCHEMA_VERSION, 'human_verified': False,
        'scope': 'All exported PRs, including zero-candidate PRs; all thread decisions retained',
        'source_collection_complete': source['complete'], 'inputs': fingerprints,
        'data_root': os.path.relpath(data, output), 'annotation_run': os.path.relpath(run_dir, output),
        'script_sha256': _sha256(Path(__file__)),
        'outputs': {name: _sha256(output / name) for name in
                    ('pr_candidates.jsonl', 'pr_summary.csv', 'statistics.json', 'report.md')},
    })
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--run-dir', type=Path, default=Path('data/annotation/full-20260926'))
    parser.add_argument('--output', type=Path, default=Path('data/pr-candidates/full-20260926'))
    args = parser.parse_args()
    print(json.dumps(build(args.data, args.run_dir, args.output)['totals'], ensure_ascii=False, indent=2))
