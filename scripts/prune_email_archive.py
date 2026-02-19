#!/usr/bin/env python3
"""
Email Archive Pruning Script for ~/docs/emails/

POLICY (chosen 2026-02-19):
    The email system is 5 days old and already has 492 files (~150/day).
    At that rate, yearly accumulation would be ~54,750 files.

    Since all emails are currently very recent (within 90 days), the
    time-based tiered approach (90d/365d) makes no sense yet. Instead
    we use a COMBINED policy that will scale well long-term:

    Tier 1 — Last 7 days: KEEP ALL (full retention, nothing pruned)
    Tier 2 — 8–90 days:   KEEP ALL (still recent, full retention)
    Tier 3 — 91–365 days: Keep 1 email per DAY (prune duplicates within same day)
    Tier 4 — Over 1 year: Keep 1 email per WEEK (Sunday's first, or nearest)

    Special rules:
    - NEVER delete emails with attachments (or linked to attachments/)
    - NEVER delete index.json (it is the live index, not an archive file)
    - Always keep emails TO/FROM authoritative contacts on any day
    - Dry-run by default; --execute required to actually delete

    The index.json is updated in-place when files are deleted.

Usage:
    python3 prune_email_archive.py --dry-run     (default, show what would happen)
    python3 prune_email_archive.py --execute     (actually delete)
    python3 prune_email_archive.py --summary     (just print stats, no action)
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, date, timedelta
from pathlib import Path

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

EMAIL_DIR = Path('/home/claude/docs/emails')
INDEX_FILE = EMAIL_DIR / 'index.json'
ATTACHMENTS_DIR = EMAIL_DIR / 'attachments'
WHITELIST_FILE = Path('/home/claude/iris/config/email-whitelist.json')

# Authoritative contacts — emails to/from these are always kept
# Loaded dynamically from config/email-whitelist.json (gitignored) to keep
# personal addresses out of the public repo.
def _load_authoritative_contacts() -> set:
    if WHITELIST_FILE.exists():
        try:
            data = json.loads(WHITELIST_FILE.read_text())
            contacts = set()
            for entry in data.get('authoritative', []):
                if isinstance(entry, dict) and 'email' in entry:
                    contacts.add(entry['email'].lower())
                elif isinstance(entry, str):
                    contacts.add(entry.lower())
            if contacts:
                return contacts
        except Exception:
            pass
    # Fallback: empty set — no emails will be "protected" by contact status
    # (all pruning still respects age tiers; only the contact-based keep rule is disabled)
    print("WARNING: config/email-whitelist.json not found or unreadable. "
          "Authoritative-contact keep rule is disabled.", file=sys.stderr)
    return set()

AUTHORITATIVE_CONTACTS = _load_authoritative_contacts()

# Tier boundaries (in days from today)
TIER1_MAX_AGE = 7     # 0-7 days: keep all
TIER2_MAX_AGE = 90    # 8-90 days: keep all
TIER3_MAX_AGE = 365   # 91-365 days: keep 1 per day
# > 365 days: keep 1 per week


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def parse_filename_date(filename: str) -> date | None:
    """Extract date from filename like 20260215_082914_Subject_hash.txt"""
    m = re.match(r'^(\d{4})(\d{2})(\d{2})_', filename)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def parse_filename_datetime(filename: str) -> datetime | None:
    """Extract full datetime from filename like 20260215_082914_..."""
    m = re.match(r'^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})_', filename)
    if m:
        try:
            return datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), int(m.group(5)), int(m.group(6))
            )
        except ValueError:
            return None
    return None


def week_key(d: date) -> str:
    """Return ISO year-week string for a date (e.g. '2026-W07')"""
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def load_index() -> dict:
    if not INDEX_FILE.exists():
        return {}
    with open(INDEX_FILE, 'r') as f:
        return json.load(f)


def save_index(index: dict, dry_run: bool) -> None:
    if dry_run:
        print(f"  [DRY-RUN] Would update {INDEX_FILE} ({len(index)} entries)")
        return
    tmp = INDEX_FILE.with_suffix('.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(index, f, indent=2)
    tmp.rename(INDEX_FILE)
    print(f"  Updated {INDEX_FILE} ({len(index)} entries remaining)")


def has_attachment(entry: dict) -> bool:
    """Return True if the index entry has real attachments."""
    attachments = entry.get('attachments', [])
    return bool(attachments)


def is_authoritative(entry: dict) -> bool:
    """Return True if sender or recipient is an authoritative contact."""
    from_addr = entry.get('from', '') or ''
    to_addr = entry.get('to', '') or ''
    combined = (from_addr + ' ' + to_addr).lower()
    for contact in AUTHORITATIVE_CONTACTS:
        if contact in combined:
            return True
    return False


# --------------------------------------------------------------------------
# Core pruning logic
# --------------------------------------------------------------------------

def classify_files(index: dict, today: date) -> dict:
    """
    Classify each file as keep/prune/protected and return a report dict.

    Returns:
        {
          'keep': [list of filenames],
          'prune': [list of filenames],
          'protected': [list of (filename, reason)],
          'unknown': [list of filenames with no parseable date],
        }
    """
    # Build a map from filename -> index_entry
    filename_to_entry = {}
    for hash_id, entry in index.items():
        fname = entry.get('filename', '')
        if fname:
            filename_to_entry[fname] = entry

    # Collect all .txt files (excluding index.json)
    all_txt = sorted([
        f.name for f in EMAIL_DIR.iterdir()
        if f.is_file() and f.suffix == '.txt'
    ])

    # Group files by date and tier
    by_day: dict[date, list[str]] = defaultdict(list)
    unknown = []

    for fname in all_txt:
        d = parse_filename_date(fname)
        if d is None:
            unknown.append(fname)
        else:
            by_day[d].append(fname)

    keep = []
    prune = []
    protected = []

    for day, files in sorted(by_day.items()):
        age = (today - day).days

        # Sort files by their embedded time so we deterministically pick the
        # "first" one for sparse tiers.
        def sort_key(f):
            dt = parse_filename_datetime(f)
            return dt or datetime.min

        files_sorted = sorted(files, key=sort_key)

        if age <= TIER2_MAX_AGE:
            # Tier 1 & 2: Keep all
            keep.extend(files_sorted)
            continue

        if age <= TIER3_MAX_AGE:
            # Tier 3 (91–365 days): keep 1 per day
            # But always keep files with attachments or authoritative contacts
            protected_today = []
            candidates = []
            for fname in files_sorted:
                entry = filename_to_entry.get(fname, {})
                if has_attachment(entry):
                    protected_today.append((fname, 'has attachments'))
                elif is_authoritative(entry):
                    protected_today.append((fname, 'authoritative contact'))
                else:
                    candidates.append(fname)

            for fname, reason in protected_today:
                protected.append((fname, reason))

            if candidates:
                keep.append(candidates[0])  # Keep the oldest on this day
                prune.extend(candidates[1:])
            continue

        # Tier 4 (> 365 days): keep 1 per week
        wk = week_key(day)
        # We'll handle this in a second pass below
        by_day[day] = files_sorted  # re-store sorted

    # Second pass for tier 4 (> 365 days)
    by_week: dict[str, list[tuple[date, str]]] = defaultdict(list)
    for day, files in sorted(by_day.items()):
        age = (today - day).days
        if age > TIER3_MAX_AGE:
            for fname in files:
                by_week[week_key(day)].append((day, fname))

    for wk, day_files in sorted(by_week.items()):
        # Separate protected and pruneable
        wk_protected = []
        wk_candidates = []
        for day, fname in day_files:
            entry = filename_to_entry.get(fname, {})
            if has_attachment(entry):
                wk_protected.append((fname, 'has attachments'))
            elif is_authoritative(entry):
                wk_protected.append((fname, 'authoritative contact'))
            else:
                wk_candidates.append((day, fname))

        for fname, reason in wk_protected:
            protected.append((fname, reason))

        if wk_candidates:
            # Keep earliest file of the week
            wk_candidates_sorted = sorted(wk_candidates, key=lambda x: (x[0], x[1]))
            keep.append(wk_candidates_sorted[0][1])
            prune.extend(f for _, f in wk_candidates_sorted[1:])

    return {
        'keep': keep,
        'prune': prune,
        'protected': protected,
        'unknown': unknown,
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Prune ~/docs/emails/ email archive per retention policy'
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', default=True,
                      help='Show what would be pruned without deleting (default)')
    mode.add_argument('--execute', action='store_true', default=False,
                      help='Actually delete files and update index.json')
    mode.add_argument('--summary', action='store_true', default=False,
                      help='Print statistics only, no file listing')
    args = parser.parse_args()

    dry_run = not args.execute
    summary_only = args.summary

    today = date.today()
    print(f"Email Archive Pruner — {today}")
    print(f"Archive dir : {EMAIL_DIR}")
    print(f"Mode        : {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print()

    # Load index
    index = load_index()
    print(f"Index entries : {len(index)}")

    # Count files
    all_txt = [f for f in EMAIL_DIR.iterdir() if f.is_file() and f.suffix == '.txt']
    print(f"Email files   : {len(all_txt)}")

    # Classify
    result = classify_files(index, today)

    keep = result['keep']
    prune = result['prune']
    protected = result['protected']
    unknown = result['unknown']

    # Stats
    total = len(keep) + len(prune) + len(protected) + len(unknown)
    print()
    print(f"=== Classification Results ===")
    print(f"  Keep (within retention)  : {len(keep)}")
    print(f"  Protected (special rules): {len(protected)}")
    print(f"  Unknown (no date in name): {len(unknown)}")
    print(f"  PRUNE                    : {len(prune)}")
    print(f"  Total classified         : {total}")

    if prune:
        # Estimate space savings
        prune_bytes = sum(
            (EMAIL_DIR / f).stat().st_size
            for f in prune
            if (EMAIL_DIR / f).exists()
        )
        print(f"  Estimated space freed    : {prune_bytes / 1024:.1f} KB")

    if not summary_only and prune:
        print()
        print(f"=== Files to prune ({len(prune)}) ===")
        for fname in sorted(prune):
            size = 0
            p = EMAIL_DIR / fname
            if p.exists():
                size = p.stat().st_size
            print(f"  {fname}  ({size} bytes)")

    if not summary_only and protected:
        print()
        print(f"=== Protected files ({len(protected)}) ===")
        for fname, reason in protected:
            print(f"  {fname}  [{reason}]")

    if unknown:
        print()
        print(f"=== Files with unparseable dates (kept) ({len(unknown)}) ===")
        for fname in unknown:
            print(f"  {fname}")

    if not prune:
        print()
        print("Nothing to prune — all files are within retention policy.")
        print("(The archive is only 5 days old; pruning activates after 90 days.)")
        return 0

    if dry_run:
        print()
        print("=== DRY-RUN: No files were deleted. ===")
        print("Run with --execute to apply pruning.")
        return 0

    # --- EXECUTE ---
    print()
    print(f"=== Executing: deleting {len(prune)} files ===")

    # Build set of hashes to remove from index
    filename_to_hash = {}
    for hash_id, entry in index.items():
        fname = entry.get('filename', '')
        if fname:
            filename_to_hash[fname] = hash_id

    deleted_count = 0
    failed_count = 0
    removed_hashes = []

    for fname in prune:
        fpath = EMAIL_DIR / fname
        try:
            if fpath.exists():
                fpath.unlink()
                deleted_count += 1
                print(f"  Deleted: {fname}")
            else:
                print(f"  Missing (skipped): {fname}")

            # Remove from index
            hash_id = filename_to_hash.get(fname)
            if hash_id and hash_id in index:
                removed_hashes.append(hash_id)
        except Exception as e:
            print(f"  ERROR deleting {fname}: {e}")
            failed_count += 1

    # Update index
    for hash_id in removed_hashes:
        del index[hash_id]

    save_index(index, dry_run=False)

    print()
    print(f"=== Done ===")
    print(f"  Deleted   : {deleted_count}")
    print(f"  Failed    : {failed_count}")
    print(f"  Index entries removed: {len(removed_hashes)}")

    return 0 if failed_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
