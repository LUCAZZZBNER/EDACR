from collections import defaultdict
import re


HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
CODE_SUFFIXES = set('''v vh sv svh vhd vhdl bsv bsh scala sc c cc cpp cxx h hh hpp hxx
py pyx pxd tcl sdc xdc qsf qpf ucf pcf lpf f s s90 asm ld lds inc sh bash zsh fish
cmake mk mak make bazel bzl ninja m4 ac am meson rs go java js jsx ts tsx cs rb pl pm
lua jl m ml mli r zig cu cuh cl hip d chisel fir ll yy y lex l antlr g4 sby ys
sp spice cir lef def liberty lib upf cpf verilator vlt vwf fstf cocotb
core sbt mill blif eblif bench il firrtl prj'''.split())
CODE_NAMES = {'makefile', 'gnumakefile', 'cmakelists.txt', 'dockerfile', 'containerfile',
              'build', 'workspace', 'sconstruct', 'sconscript', 'meson.build', 'meson_options.txt',
              'configure', 'justfile', 'build.sbt', 'cargo.toml', 'pyproject.toml', 'setup.cfg',
              'tox.ini', '.bazelrc', '.gitmodules', 'requirements.txt'}


def is_code(path):
    name = path.rsplit('/', 1)[-1].lower()
    return (name in CODE_NAMES or name.rsplit('.', 1)[-1] in CODE_SUFFIXES
            or path.startswith(('.github/workflows/', '.gitlab/ci/'))
            or name.startswith(('makefile.', 'dockerfile.', 'requirements-')))


def is_bot(comment):
    user = comment.get('user') or {}
    return user.get('type') == 'Bot' or user.get('login', '').lower().endswith('[bot]')


def select_revision(comments):
    """Each rooted thread containing a non-bot casts exactly one vote."""
    by_id = {c['id']: c for c in comments}
    groups, failures = defaultdict(list), []
    for comment in comments:
        root, seen = comment, set()
        while root.get('in_reply_to_id'):
            if root['id'] in seen or root['in_reply_to_id'] not in by_id:
                root = None
                break
            seen.add(root['id'])
            root = by_id[root['in_reply_to_id']]
        if root is None:
            failures.append({'comment_id': comment['id'], 'reason': 'missing_or_cyclic_thread_root'})
        else:
            groups[root['id']].append(comment)
    revisions = defaultdict(list)
    for id, members in groups.items():
        root = by_id[id]
        if any(not is_bot(c) for c in members):
            sha = root.get('original_commit_id')
            if not sha:
                failures.extend({'comment_id': c['id'], 'reason': 'missing_original_commit'} for c in members)
                continue
            revisions[sha].append({'root': root, 'comments': sorted(members, key=lambda c: (c['created_at'], c['id']))})
    counts = {sha: {'threads': len(threads), 'first_review': min(t['root']['created_at'] for t in threads)}
              for sha, threads in sorted(revisions.items())}
    if not counts:
        return None, [], counts, failures
    selected = min(counts, key=lambda sha: (-counts[sha]['threads'], counts[sha]['first_review'], sha))
    return selected, sorted(revisions[selected], key=lambda t: t['root']['id']), counts, failures


def parse_patch(patch, *, strict=True):
    """Return numbered original/new lines and validate every declared hunk length."""
    lines, positions, hunks = {'LEFT': {}, 'RIGHT': {}}, {}, []
    remaining = None
    old = new = position = 0
    for raw in patch.splitlines():
        match = HUNK.match(raw)
        if match:
            if strict and remaining is not None and remaining != [0, 0]:
                raise ValueError('truncated_patch_hunk')
            old, old_count, new, new_count = match.groups()
            old, new = int(old), int(new)
            remaining = [int(old_count or 1), int(new_count or 1)]
            hunks.append({'old_start': old, 'old_count': remaining[0],
                          'new_start': new, 'new_count': remaining[1]})
            if len(hunks) > 1:
                position += 1
            continue
        if remaining is None or raw.startswith('\\ No newline'):
            continue
        position += 1
        if not raw or raw[0] not in ' +-':
            raise ValueError('invalid_patch_line')
        sides = []
        if raw[0] in ' -':
            lines['LEFT'][old] = raw[1:]
            sides.append(('LEFT', old))
            old += 1
            remaining[0] -= 1
        if raw[0] in ' +':
            lines['RIGHT'][new] = raw[1:]
            sides.append(('RIGHT', new))
            new += 1
            remaining[1] -= 1
        positions[position] = sides
    if strict and remaining is not None and remaining != [0, 0]:
        raise ValueError('truncated_patch_hunk')
    return lines, positions, hunks


def locate(root, files):
    path = root.get('path')
    matches = [f for f in files if path in (f['filename'], f.get('previous_filename'))]
    if len(matches) != 1:
        return None, 'path_not_in_selected_diff'
    file = matches[0]
    try:
        full, positions, _ = parse_patch(file.get('patch', ''))
        original, _, original_hunks = parse_patch(root.get('diff_hunk') or '', strict=False)
    except ValueError as exc:
        return None, str(exc)
    side = root.get('side')
    end = root.get('original_line')
    start = root.get('original_start_line') or end
    method = 'original_line'
    if end is None:
        # Legacy position counts from the FIRST hunk in the full file diff, including hunk headers.
        # Use it only when original and selected hunks agree at the recovered line.
        choices = positions.get(root.get('original_position'), [])
        if side:
            choices = [c for c in choices if c[0] == side]
        elif len(choices) > 1:
            choices = [c for c in choices if c[0] == 'RIGHT']
        if len(choices) != 1:
            return None, 'missing_reliable_original_anchor'
        side, end = choices[0]
        start = end
        method = 'original_position_verified_hunk'
    if side not in ('LEFT', 'RIGHT'):
        return None, 'missing_diff_side'
    if root.get('start_side') and root['start_side'] != side and start != end:
        return None, 'cross_side_range'
    if not isinstance(start, int) or not isinstance(end, int) or start <= 0 or start > end:
        return None, 'invalid_line_range'
    if not original_hunks:
        return None, 'missing_original_hunk'
    # All available original context must agree on BOTH sides. This validates the candidate baseline.
    for s in ('LEFT', 'RIGHT'):
        for line, text in original[s].items():
            if line in full[s] and full[s][line] != text:
                return None, 'original_hunk_conflicts_with_selected_baseline'
    for line in range(start, end + 1):
        if line not in original[side] or line not in full[side] or original[side][line] != full[side][line]:
            return None, 'anchor_not_verified_in_selected_diff'
    return {'path': file.get('previous_filename', file['filename']) if side == 'LEFT' else file['filename'],
            'side': side.lower(), 'from_line': start, 'to_line': end, 'method': method}, None


def region_evidence(anchor, file, later_files):
    """Signal only: later diff changes a reviewed line (or inserts directly after it)."""
    if anchor['side'] != 'right':
        return {'status': 'not_assessed', 'reason': 'LEFT_anchor_is_on_source_revision'}
    matches = [f for f in later_files if file['filename'] in (f['filename'], f.get('previous_filename'))]
    if not matches:
        return {'status': 'verified', 'region_modified': False}
    if matches[0].get('binary') or matches[0].get('gitlink'):
        return {'status': 'not_assessed', 'reason': 'later_file_has_no_text_diff'}
    parse_patch(matches[0].get('patch', ''))
    # Hunk context is not evidence of an edit; enumerate only deletion and insertion positions.
    old = None
    edits = []
    for line in matches[0].get('patch', '').splitlines():
        m = HUNK.match(line)
        if m:
            old = int(m.group(1))
        elif old is not None and line.startswith('-'):
            edits.append(old)
            old += 1
        elif old is not None and line.startswith('+'):
            edits.append(max(1, old - 1))
        elif old is not None and line.startswith(' '):
            old += 1
    return {'status': 'verified', 'region_modified': any(anchor['from_line'] <= n <= anchor['to_line'] for n in edits),
            'later_path': matches[0]['filename']}
