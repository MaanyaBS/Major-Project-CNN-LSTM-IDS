from pathlib import Path
import json
import pickle
import shutil
import tempfile

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


# ============================================================
# MU-IoT HANDOFF V3
# Cleaned-master / canonical-row implementation
# ============================================================

ROOT = Path(r"D:\Major_Project")

CLEANED = ROOT / r"dataset\processed\mu_iot\mu_iot_cleaned.csv"
CFG = ROOT / r"config\mu_iot_feature_sets.json"

OUT = ROOT / r"dataset\processed\mu_iot\handoff_v3"

CHUNK = 100_000
BLOCK_SIZE = 10_000
MIN_BLOCK = 20
SEED = 42

HELDOUT = {
    "MU_SESSION_031",
    "MU_SESSION_013",
    "MU_SESSION_021",
    "MU_SESSION_026",
}

SPLITS = {
    "train": 0,
    "val": 1,
    "test_within": 2,
    "test_heldout": 3,
}

CAPS = {
    "train": 500_000,
    "val": 100_000,
    "test_within": 150_000,
}

HELDOUT_SESSION_CAP = 200_000
PILOT_TARGET = 150_000

BASE_KEY = "paper_top48_coverage95_nonconstant"
NEW_KEY = "paper_top48_coverage95_nonconstant_38"

REMOVE = {"FPT", "LPT"}

META_COLUMNS = [
    "row_id",
    "capture_session",
    "block_id",
    "split",
    "category_id",
]


# ============================================================
# Utilities
# ============================================================

def fail(msg):
    raise RuntimeError("\n[FAIL] " + msg)


def load_features():
    if not CLEANED.exists():
        fail(f"Cleaned master not found:\n{CLEANED}")

    if not CFG.exists():
        fail(f"Feature configuration not found:\n{CFG}")

    cfg = json.loads(CFG.read_text(encoding="utf-8"))

    feature_sets = cfg.get("feature_sets", {})

    if BASE_KEY not in feature_sets:
        fail(f"Missing existing feature key: {BASE_KEY}")

    base = list(feature_sets[BASE_KEY])

    if len(base) != 40:
        fail(
            f"Expected existing 40-feature key to contain 40 features; "
            f"found {len(base)}."
        )

    if not REMOVE.issubset(set(base)):
        fail(
            "Existing 40-feature key does not contain both "
            "FPT and LPT."
        )

    features = [x for x in base if x not in REMOVE]

    if len(features) != 38:
        fail(f"Expected 38 features after FPT/LPT removal; got {len(features)}.")

    # Preserve the existing 40-feature key unchanged.
    if NEW_KEY not in feature_sets:
        feature_sets[NEW_KEY] = features
        CFG.write_text(
            json.dumps(cfg, indent=2),
            encoding="utf-8",
        )
        print(f"[INFO] Added feature key: {NEW_KEY}")
    else:
        existing = list(feature_sets[NEW_KEY])
        if existing != features:
            fail(
                f"{NEW_KEY} already exists but does not exactly match "
                f"the existing 40-feature key minus FPT/LPT."
            )

    if "FPT" in features or "LPT" in features:
        fail("FPT/LPT leakage in final feature list.")

    print(f"[INFO] Base feature count : {len(base)}")
    print(f"[INFO] Final feature count: {len(features)}")
    print("[INFO] FPT/LPT removed from final feature list.")

    return features


def inspect_header(features):
    header = pd.read_csv(CLEANED, nrows=0)

    cols = list(header.columns)
    required = {"capture_session", "category"}

    missing_required = required - set(cols)

    if missing_required:
        fail(
            f"Cleaned master is missing required columns: "
            f"{sorted(missing_required)}"
        )

    missing_features = [f for f in features if f not in cols]

    if missing_features:
        fail(
            "Final feature list contains columns missing from cleaned master:\n"
            + "\n".join(missing_features)
        )

    if "split" in cols:
        print(
            "[WARN] Cleaned master contains a split column, "
            "but V3 deliberately derives split from session/row order."
        )

    print(f"[INFO] Cleaned-master columns: {len(cols)}")
    print("[INFO] Required feature columns confirmed.")


# ============================================================
# Canonical session discovery
# ============================================================

def discover_sessions():
    """
    Scan only capture_session/category.

    Produces contiguous canonical session regions:
        row_start inclusive
        row_end exclusive
        session
        category

    row_id is exactly the zero-based position in the cleaned CSV.
    """

    print("\n[1/9] Discovering canonical session regions...")

    regions = []

    global_row = 0

    current_session = None
    current_category = None
    current_start = None

    previous_sessions = set()

    for chunk in pd.read_csv(
        CLEANED,
        usecols=["capture_session", "category"],
        chunksize=CHUNK,
    ):
        sessions = chunk["capture_session"].astype(str).to_numpy()
        categories = chunk["category"].astype(str).to_numpy()

        for i in range(len(chunk)):
            session = sessions[i]
            category = categories[i]
            row_id = global_row + i

            if current_session is None:
                current_session = session
                current_category = category
                current_start = row_id
                continue

            if session != current_session:

                if current_session in previous_sessions:
                    fail(
                        f"Session {current_session} is non-contiguous "
                        f"in the cleaned master."
                    )

                regions.append(
                    {
                        "session": current_session,
                        "category": current_category,
                        "start": current_start,
                        "end": row_id,
                    }
                )

                previous_sessions.add(current_session)

                current_session = session
                current_category = category
                current_start = row_id

            elif category != current_category:
                fail(
                    f"Session {current_session} changes category at "
                    f"canonical row_id {row_id}: "
                    f"{current_category} -> {category}"
                )

        global_row += len(chunk)

    if current_session is not None:
        if current_session in previous_sessions:
            fail(
                f"Session {current_session} is non-contiguous "
                f"at the end of the cleaned master."
            )

        regions.append(
            {
                "session": current_session,
                "category": current_category,
                "start": current_start,
                "end": global_row,
            }
        )

    if global_row != 24_171_263:
        print(
            f"[INFO] Cleaned-master row count detected: {global_row:,}"
        )

    if len(regions) != 32:
        fail(
            f"Expected 32 contiguous sessions; found {len(regions)}."
        )

    print(f"[OK] Canonical rows: {global_row:,}")
    print(f"[OK] Contiguous sessions: {len(regions)}")

    categories = sorted({r["category"] for r in regions})

    print(f"[OK] Session-level categories: {len(categories)}")
    print(f"[INFO] Categories: {categories}")

    if len(categories) != 7:
        fail(
            f"Expected 7 categories; found {len(categories)}: {categories}"
        )

    return regions, global_row


# ============================================================
# Split assignment
# ============================================================

def assign_split_regions(session_regions):
    """
    Held-out sessions:
        entire session -> test_heldout

    Other sessions:
        chronological session-local 70/15/15 split.

    The split itself is represented as a half-open canonical row interval.
    """

    print("\n[2/9] Assigning train/val/test regions...")

    split_regions = []

    for r in session_regions:

        session = r["session"]
        category = r["category"]
        start = r["start"]
        end = r["end"]
        n = end - start

        if session in HELDOUT:

            split_regions.append(
                {
                    "session": session,
                    "category": category,
                    "split": "test_heldout",
                    "start": start,
                    "end": end,
                }
            )

            continue

        train_end = start + int(n * 0.70)
        val_end = start + int(n * 0.85)

        boundaries = [
            ("train", start, train_end),
            ("val", train_end, val_end),
            ("test_within", val_end, end),
        ]

        for split, a, z in boundaries:
            if z <= a:
                continue

            split_regions.append(
                {
                    "session": session,
                    "category": category,
                    "split": split,
                    "start": a,
                    "end": z,
                }
            )

    print(f"[OK] Split regions: {len(split_regions)}")

    counts = {}

    for r in split_regions:
        counts[r["split"]] = counts.get(r["split"], 0) + (
            r["end"] - r["start"]
        )

    for split in SPLITS:
        print(
            f"  {split:<14}: "
            f"{counts.get(split, 0):>12,} rows"
        )

    return split_regions


# ============================================================
# Candidate complete blocks
# ============================================================

def create_candidate_blocks(split_regions):
    """
    Create blocks entirely inside one:
        session + category + split

    Every block:
        - has >= MIN_BLOCK rows
        - has <= BLOCK_SIZE rows
        - has consecutive canonical row_ids
        - never crosses session/split/category boundary
    """

    print("\n[3/9] Creating complete candidate blocks...")

    blocks = []
    block_id = 0

    for r in split_regions:

        start = r["start"]
        end = r["end"]

        cursor = start

        while cursor < end:
            remaining = end - cursor

            if remaining < MIN_BLOCK:
                # Deliberately discard incomplete tail.
                break

            size = min(BLOCK_SIZE, remaining)

            if size < MIN_BLOCK:
                break

            block = {
                "block_id": block_id,
                "session": r["session"],
                "category": r["category"],
                "split": r["split"],
                "start": cursor,
                "end": cursor + size,
                "nrows": size,
            }

            blocks.append(block)
            block_id += 1

            cursor += size

    print(f"[OK] Candidate blocks: {len(blocks):,}")

    if not blocks:
        fail("No candidate blocks were created.")

    return blocks


# ============================================================
# Deterministic block selection
# ============================================================

def select_blocks(candidates):
    """
    Select complete contiguous blocks using PER-CLASS caps while
    explicitly spreading selection across sessions and timelines.

    Rules:
        train        <= 500k per category
        val          <= 100k per category
        test_within  <= 150k per category
        each heldout session <= 200k

    Selection is whole-block only. No random row-level sampling.

    Strategy:
        - For train/val/test_within, selection is performed
          independently for every (split, category).
        - Sessions are visited round-robin so as many sessions
          as possible contribute blocks.
        - Within every session, timeline bins are visited
          round-robin so selected blocks are distributed across
          the session timeline.
        - A deterministic seed is used only to vary the order
          of eligible sessions/bins.
        - Final package order is restored to canonical row order.
    """

    print(
        "\n[4/9] Selecting complete blocks with "
        "per-class caps + session/timeline spreading..."
    )

    SEED = 42
    TIMELINE_BINS = 20

    # Canonical candidate order.
    candidates = sorted(
        candidates,
        key=lambda b: (
            b["start"],
            b["end"],
            b["block_id"],
        ),
    )

    categories = sorted(
        {b["category"] for b in candidates}
    )

    if len(categories) != 7:
        fail(
            f"Candidate blocks contain {len(categories)} categories, "
            f"expected 7."
        )

    selected = []
    selected_ids = set()

    # --------------------------------------------------------
    # Per-class accounting.
    # --------------------------------------------------------

    class_counts = {
        (split, category): 0
        for split in CAPS
        for category in categories
    }

    heldout_counts = {
        s: 0
        for s in HELDOUT
    }

    def allowed(block):
        split = block["split"]
        category = block["category"]
        n = block["nrows"]

        if split == "test_heldout":
            used = heldout_counts.get(
                block["session"],
                0,
            )

            return (
                used + n
                <= HELDOUT_SESSION_CAP
            )

        used = class_counts[
            (split, category)
        ]

        return (
            used + n
            <= CAPS[split]
        )

    def add(block):
        bid = block["block_id"]

        if bid in selected_ids:
            return False

        if not allowed(block):
            return False

        selected.append(block)
        selected_ids.add(bid)

        split = block["split"]
        category = block["category"]
        n = block["nrows"]

        if split == "test_heldout":
            heldout_counts[
                block["session"]
            ] += n
        else:
            class_counts[
                (split, category)
            ] += n

        return True

    # --------------------------------------------------------
    # Timeline-bin helper.
    #
    # The bin is calculated relative to the COMPLETE session,
    # not relative to the split. Therefore train/val/test blocks
    # can collectively cover the complete session timeline.
    # --------------------------------------------------------

    session_end = {}

    for b in candidates:
        s = b["session"]

        if (
            s not in session_end
            or b["end"] > session_end[s]
        ):
            session_end[s] = b["end"]

    def timeline_bin(block):
        s = block["session"]
        end = session_end[s]

        if end <= 0:
            return 0

        fraction = (
            block["start"] / end
        )

        value = int(
            fraction * TIMELINE_BINS
        )

        return min(
            TIMELINE_BINS - 1,
            max(0, value),
        )

    # --------------------------------------------------------
    # Build lookup:
    #
    # (split, category, session) -> timeline bins -> blocks
    # --------------------------------------------------------

    grouped = {}

    for b in candidates:

        key = (
            b["split"],
            b["category"],
            b["session"],
        )

        if key not in grouped:
            grouped[key] = {
                i: []
                for i in range(TIMELINE_BINS)
            }

        grouped[key][
            timeline_bin(b)
        ].append(b)

    for key in grouped:
        for bin_id in grouped[key]:
            grouped[key][bin_id].sort(
                key=lambda b: (
                    b["start"],
                    b["end"],
                    b["block_id"],
                )
            )

    # --------------------------------------------------------
    # Deterministic helper to create a session order.
    #
    # We shuffle the session order, but selection itself remains
    # deterministic because the seed is fixed.
    # --------------------------------------------------------

    def session_order(sessions, salt):
        local_rng = np.random.default_rng(
            SEED + salt
        )

        result = list(sessions)
        local_rng.shuffle(result)

        return result

    # --------------------------------------------------------
    # Select one split/category combination.
    #
    # Phase A:
    #   one block from as many sessions as possible.
    #
    # Phase B:
    #   continue round-robin over sessions and timeline bins.
    #
    # This is the key difference from the previous selector.
    # --------------------------------------------------------

    def select_split_category(split, category):

        cap = CAPS[split]

        sessions = sorted({
            b["session"]
            for b in candidates
            if (
                b["split"] == split
                and b["category"] == category
            )
        })

        if not sessions:
            return

        sessions = session_order(
            sessions,
            (
                abs(hash(split)) % 1000
                + abs(hash(category)) % 100
            ),
        )

        # Each session gets its own rotating timeline-bin pointer.
        bin_order = {}
        bin_pointer = {}

        for session in sessions:

            available_bins = [
                i
                for i in range(TIMELINE_BINS)
                if grouped.get(
                    (split, category, session),
                    {}
                ).get(i, [])
            ]

            local_rng = np.random.default_rng(
                SEED
                + 1000
                + len(session)
                + sum(
                    ord(c)
                    for c in session
                )
            )

            local_rng.shuffle(
                available_bins
            )

            bin_order[session] = available_bins
            bin_pointer[session] = 0

        # ----------------------------------------------------
        # Phase A: session coverage.
        #
        # Give every session one opportunity before returning
        # to a session that already contributed.
        # ----------------------------------------------------

        progress = True

        while progress:

            progress = False

            for session in sessions:

                if class_counts[
                    (split, category)
                ] >= cap:
                    return

                bins = bin_order[session]

                if not bins:
                    continue

                # Find the next non-empty timeline bin.
                found = None

                for _ in range(len(bins)):

                    idx = (
                        bin_pointer[session]
                        % len(bins)
                    )

                    bin_id = bins[idx]

                    bin_pointer[session] += 1

                    blocks = grouped[
                        (split, category, session)
                    ][bin_id]

                    if blocks:
                        found = blocks
                        break

                if found is None:
                    continue

                # Take the earliest remaining block in this
                # timeline bin.
                for block in found:

                    if add(block):
                        progress = True
                        break

        # ----------------------------------------------------
        # Phase B: continued session/timeline round-robin.
        # ----------------------------------------------------

        progress = True

        while progress:

            progress = False

            for session in sessions:

                if class_counts[
                    (split, category)
                ] >= cap:
                    return

                bins = bin_order[session]

                if not bins:
                    continue

                # Rotate through bins for this session.
                for _ in range(len(bins)):

                    idx = (
                        bin_pointer[session]
                        % len(bins)
                    )

                    bin_id = bins[idx]

                    bin_pointer[session] += 1

                    blocks = grouped[
                        (split, category, session)
                    ][bin_id]

                    for block in blocks:

                        if add(block):
                            progress = True
                            break

                    if progress:
                        break

    # --------------------------------------------------------
    # Ensure every category has representation.
    # --------------------------------------------------------

    for category in categories:

        options = [
            b
            for b in candidates
            if b["category"] == category
        ]

        added = False

        for preferred_split in [
            "train",
            "val",
            "test_within",
            "test_heldout",
        ]:

            for b in options:

                if b["split"] != preferred_split:
                    continue

                if add(b):
                    added = True
                    break

            if added:
                break

        if not added:
            fail(
                f"Could not select a complete block for "
                f"category {category}."
            )

    # --------------------------------------------------------
    # Main selection.
    #
    # Each split/category is handled independently, preventing
    # early sessions from consuming another session's quota.
    # --------------------------------------------------------

    split_category_order = [
        "train",
        "val",
        "test_within",
    ]

    for split in split_category_order:

        for category in categories:

            select_split_category(
                split,
                category,
            )

    # --------------------------------------------------------
    # Held-out selection.
    #
    # Each held-out session has its own independent cap.
    # Timeline spreading is performed across the entire
    # held-out session.
    # --------------------------------------------------------

    for session in HELDOUT:

        session_blocks = [
            b
            for b in candidates
            if (
                b["split"] == "test_heldout"
                and b["session"] == session
            )
        ]

        if not session_blocks:
            fail(
                f"No candidate blocks found for "
                f"held-out session {session}."
            )

        bins = {
            i: []
            for i in range(TIMELINE_BINS)
        }

        for b in session_blocks:
            bins[
                timeline_bin(b)
            ].append(b)

        for bin_id in bins:
            bins[bin_id].sort(
                key=lambda b: (
                    b["start"],
                    b["end"],
                    b["block_id"],
                )
            )

        available_bins = [
            i
            for i in range(TIMELINE_BINS)
            if bins[i]
        ]

        local_rng = np.random.default_rng(
            SEED
            + 5000
            + sum(ord(c) for c in session)
        )

        local_rng.shuffle(
            available_bins
        )

        pointer = 0

        # Round-robin over timeline bins.
        progress = True

        while progress:

            progress = False

            if (
                heldout_counts[session]
                >= HELDOUT_SESSION_CAP
            ):
                break

            for bin_id in available_bins:

                if (
                    heldout_counts[session]
                    >= HELDOUT_SESSION_CAP
                ):
                    break

                blocks = bins[bin_id]

                while pointer < len(blocks):

                    block = blocks[pointer]
                    pointer += 1

                    if add(block):
                        progress = True
                        break

                if progress:
                    break

    # --------------------------------------------------------
    # Final deterministic canonical ordering.
    # --------------------------------------------------------

    selected.sort(
        key=lambda b: (
            b["start"],
            b["end"],
            b["block_id"],
        )
    )

    # Assign package-order positions.
    package_cursor = 0

    for b in selected:

        b["package_start"] = package_cursor

        b["package_end"] = (
            package_cursor
            + b["nrows"]
        )

        package_cursor += b["nrows"]

    # --------------------------------------------------------
    # Report counts.
    # --------------------------------------------------------

    print(
        "\n[OK] Selected blocks:",
        f"{len(selected):,}",
    )

    print("\nPer-class split counts:")

    for split in [
        "train",
        "val",
        "test_within",
    ]:

        print(f"\n  {split}:")

        for category in categories:

            n = class_counts[
                (split, category)
            ]

            print(
                f"    {category:<20}: "
                f"{n:>10,}"
            )

    print("\nHeld-out session counts:")

    for session in HELDOUT:

        n = heldout_counts[session]

        print(
            f"  {session:<18}: "
            f"{n:>10,}"
        )

    # --------------------------------------------------------
    # Explicit cap validation.
    # --------------------------------------------------------

    for split in CAPS:

        for category in categories:

            n = class_counts[
                (split, category)
            ]

            if n > CAPS[split]:

                fail(
                    f"{split}/{category} cap exceeded: "
                    f"{n:,} > {CAPS[split]:,}"
                )

    for session in HELDOUT:

        n = heldout_counts[session]

        if n > HELDOUT_SESSION_CAP:

            fail(
                f"Held-out session {session} cap exceeded: "
                f"{n:,} > "
                f"{HELDOUT_SESSION_CAP:,}"
            )

    # Seven-class coverage.
    selected_categories = {
        b["category"]
        for b in selected
    }

    if selected_categories != set(categories):

        fail(
            "Selected package does not contain all 7 categories."
        )

    print(
        "\n[OK] Per-class caps, session coverage, "
        "and timeline-spread selection complete."
    )

    return selected


# ============================================================
# Manifest
# ============================================================

def write_manifest(blocks, path):
    rows = []

    for b in blocks:
        rows.append(
            {
                "block_id": b["block_id"],
                "session": b["session"],
                "category": b["category"],
                "split": b["split"],
                "row_start": b["start"],
                "row_end_exclusive": b["end"],
                "nrows": b["nrows"],
                "package_start": b["package_start"],
                "package_end_exclusive": b["package_end"],
            }
        )

    pd.DataFrame(rows).to_csv(
        path,
        index=False,
    )


# ============================================================
# Interval streaming
# ============================================================

def build_selected_intervals(blocks):
    """
    Returns sorted canonical intervals.

    Each tuple:
        start, end, block
    """

    return [
        (b["start"], b["end"], b)
        for b in sorted(
            blocks,
            key=lambda x: x["start"],
        )
    ]


def rows_for_chunk(chunk_start, chunk_end, intervals, pointer):
    """
    Find selected intervals intersecting a CSV chunk.

    Returns:
        list of (local_start, local_end, block)

    and updated pointer.
    """

    result = []

    while pointer < len(intervals):

        a, z, block = intervals[pointer]

        if z <= chunk_start:
            pointer += 1
            continue

        if a >= chunk_end:
            break

        local_a = max(a, chunk_start) - chunk_start
        local_z = min(z, chunk_end) - chunk_start

        if local_a < local_z:
            result.append(
                (local_a, local_z, block)
            )

        if z <= chunk_end:
            pointer += 1
        else:
            break

    return result, pointer


# ============================================================
# Category mapping
# ============================================================

def build_label_mapping(blocks):
    categories = sorted(
        {b["category"] for b in blocks}
    )

    mapping = {
        category: i
        for i, category in enumerate(categories)
    }

    return mapping


# ============================================================
# Selected-data validation / numeric conversion
# ============================================================

def prepare_features(frame, features):
    x = frame[features].apply(
        pd.to_numeric,
        errors="coerce",
    )

    arr = x.to_numpy(dtype=np.float64)

    if not np.isfinite(arr).all():
        bad = int((~np.isfinite(arr)).sum())
        fail(
            f"Selected cleaned-master rows contain {bad:,} "
            f"non-finite feature values."
        )

    return arr


# ============================================================
# Fit train-only scaler
# ============================================================

def fit_train_scaler(blocks, features):
    """
    First complete pass over cleaned master.

    StandardScaler is fitted ONLY using selected train blocks.
    """

    print("\n[5/9] Fitting StandardScaler using TRAIN ONLY...")

    intervals = build_selected_intervals(blocks)

    scaler = StandardScaler()

    train_rows_seen = 0
    chunk_start = 0
    pointer = 0

    usecols = features + [
        "capture_session",
        "category",
    ]

    for chunk in pd.read_csv(
        CLEANED,
        usecols=usecols,
        chunksize=CHUNK,
    ):

        chunk_end = chunk_start + len(chunk)

        intersections, pointer = rows_for_chunk(
            chunk_start,
            chunk_end,
            intervals,
            pointer,
        )

        for local_a, local_z, block in intersections:

            if block["split"] != "train":
                continue

            part = chunk.iloc[local_a:local_z]

            arr = prepare_features(
                part,
                features,
            )

            scaler.partial_fit(arr)

            train_rows_seen += len(arr)

        chunk_start = chunk_end

    if train_rows_seen == 0:
        fail("No train rows were seen while fitting scaler.")

    print(f"[OK] Scaler training rows: {train_rows_seen:,}")

    # Store an explicit invariant.
    scaler._mu_iot_fit_split = "train"
    scaler._mu_iot_fit_rows = train_rows_seen

    return scaler, train_rows_seen


# ============================================================
# Write full package
# ============================================================

def write_full_package(
    blocks,
    features,
    scaler,
    label_mapping,
    build_dir,
):
    """
    Second complete pass.

    Reads canonical cleaned-master order and writes:
        X
        metadata

    simultaneously, guaranteeing alignment.
    """

    print("\n[6/9] Writing full float32 package...")

    total_rows = sum(
        b["nrows"]
        for b in blocks
    )

    x_path = build_dir / "mu_iot_features_38_float32.npy"

    X = np.lib.format.open_memmap(
        x_path,
        mode="w+",
        dtype=np.float32,
        shape=(total_rows, len(features)),
    )

    row_ids = np.empty(total_rows, dtype=np.int64)
    capture_sessions = np.empty(total_rows, dtype="U64")
    block_ids = np.empty(total_rows, dtype=np.int64)
    split_ids = np.empty(total_rows, dtype=np.int8)
    category_ids = np.empty(total_rows, dtype=np.int16)

    intervals = build_selected_intervals(blocks)

    chunk_start = 0
    pointer = 0

    usecols = features + [
        "capture_session",
        "category",
    ]

    written = 0

    for chunk in pd.read_csv(
        CLEANED,
        usecols=usecols,
        chunksize=CHUNK,
    ):

        chunk_end = chunk_start + len(chunk)

        intersections, pointer = rows_for_chunk(
            chunk_start,
            chunk_end,
            intervals,
            pointer,
        )

        for local_a, local_z, block in intersections:

            part = chunk.iloc[local_a:local_z]

            arr = prepare_features(
                part,
                features,
            )

            transformed = scaler.transform(
                arr
            ).astype(
                np.float32,
                copy=False,
            )

            n = len(part)

            pa = block["package_start"] + (
                max(block["start"], chunk_start)
                - block["start"]
            )

            pz = pa + n

            X[pa:pz] = transformed

            canonical_a = max(
                block["start"],
                chunk_start,
            )

            canonical_z = canonical_a + n

            row_ids[pa:pz] = np.arange(
                canonical_a,
                canonical_z,
                dtype=np.int64,
            )

            capture_sessions[pa:pz] = (
                part["capture_session"]
                .astype(str)
                .to_numpy()
            )

            block_ids[pa:pz] = block["block_id"]

            split_ids[pa:pz] = SPLITS[
                block["split"]
            ]

            category_ids[pa:pz] = label_mapping[
                block["category"]
            ]

            written += n

        chunk_start = chunk_end

    X.flush()

    if written != total_rows:
        fail(
            f"Expected to write {total_rows:,} rows, "
            f"but wrote {written:,}."
        )

    np.savez_compressed(
        build_dir / "mu_iot_meta.npz",
        row_id=row_ids,
        capture_session=capture_sessions,
        block_id=block_ids,
        split=split_ids,
        category_id=category_ids,
    )

    (build_dir / "feature_list_38.json").write_text(
        json.dumps(
            features,
            indent=2,
        ),
        encoding="utf-8",
    )

    (build_dir / "label_mapping.json").write_text(
        json.dumps(
            label_mapping,
            indent=2,
        ),
        encoding="utf-8",
    )

    with open(
        build_dir / "scaler_38.pkl",
        "wb",
    ) as f:
        pickle.dump(
            scaler,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    print(f"[OK] X shape: {X.shape}")
    print(f"[OK] X dtype: {X.dtype}")

    del X

    return total_rows


# ============================================================
# Class/split counts
# ============================================================

def write_counts(blocks, label_mapping, path):
    rows = []

    for split in SPLITS:
        for category, category_id in sorted(
            label_mapping.items(),
            key=lambda x: x[1],
        ):
            n = sum(
                b["nrows"]
                for b in blocks
                if b["split"] == split
                and b["category"] == category
            )

            rows.append(
                {
                    "split": split,
                    "split_id": SPLITS[split],
                    "category": category,
                    "category_id": category_id,
                    "rows": n,
                }
            )

    pd.DataFrame(rows).to_csv(
        path,
        index=False,
    )


# ============================================================
# Strict validator
# ============================================================

def validate_package(
    build_dir,
    blocks,
    features,
    label_mapping,
    expected_rows,
    pilot=False,
):
    print(
        "\n[VALIDATE] "
        + ("PILOT" if pilot else "FULL")
    )

    x_path = build_dir / "mu_iot_features_38_float32.npy"
    meta_path = build_dir / "mu_iot_meta.npz"

    X = np.load(
        x_path,
        mmap_mode="r",
    )

    meta = np.load(
        meta_path,
        allow_pickle=False,
    )

    # 1. Exactly 38 features.
    if len(features) != 38:
        fail("Validation: feature count is not 38.")

    # 2. FPT/LPT absent.
    if "FPT" in features or "LPT" in features:
        fail("Validation: FPT/LPT present.")

    # 3. Shape.
    if X.ndim != 2 or X.shape[1] != 38:
        fail(
            f"Validation: X shape is {X.shape}, expected (?, 38)."
        )

    if X.shape[0] != expected_rows:
        fail(
            f"Validation: X rows {X.shape[0]:,} "
            f"!= expected {expected_rows:,}."
        )

    # 4. Float32.
    if X.dtype != np.float32:
        fail(
            f"Validation: X dtype is {X.dtype}, expected float32."
        )

    # 5. Metadata alignment.
    lengths = {
        key: len(meta[key])
        for key in META_COLUMNS
    }

    if len(set(lengths.values())) != 1:
        fail(
            f"Validation: metadata lengths differ: {lengths}"
        )

    if next(iter(lengths.values())) != X.shape[0]:
        fail(
            "Validation: metadata row count does not equal X row count."
        )

    # 6. Finite X.
    if not np.isfinite(X).all():
        fail("Validation: X contains non-finite values.")

    row_id = meta["row_id"]
    session = meta["capture_session"].astype(str)
    block_id = meta["block_id"]
    split_id = meta["split"]
    category_id = meta["category_id"]

    # 7. Canonical row IDs are unique.
    if len(np.unique(row_id)) != len(row_id):
        fail("Validation: duplicate row_id detected.")

    # 8. Every metadata row corresponds to an actual canonical row.
    if np.any(row_id < 0):
        fail("Validation: negative row_id detected.")

    # For a selected package, row_ids need not be globally consecutive.
    # But every block must be consecutive.

    # 9. Block-level checks.
    unique_blocks = []

    for bid in np.unique(block_id):
        idx = np.flatnonzero(block_id == bid)

        if len(idx) < MIN_BLOCK:
            fail(
                f"Validation: block {bid} has only {len(idx)} rows."
            )

        if not np.all(
            np.diff(row_id[idx]) == 1
        ):
            fail(
                f"Validation: row_id is not consecutive "
                f"inside block {bid}."
            )

        if len(set(session[idx])) != 1:
            fail(
                f"Validation: block {bid} crosses sessions."
            )

        if len(set(split_id[idx].tolist())) != 1:
            fail(
                f"Validation: block {bid} crosses splits."
            )

        if len(set(category_id[idx].tolist())) != 1:
            fail(
                f"Validation: block {bid} crosses categories."
            )

        unique_blocks.append(bid)

    # 10. No block overlap.
    all_block_ranges = []

    for bid in unique_blocks:
        idx = np.flatnonzero(block_id == bid)
        all_block_ranges.append(
            (
                int(row_id[idx[0]]),
                int(row_id[idx[-1]]),
                int(bid),
            )
        )

    all_block_ranges.sort()

    for i in range(1, len(all_block_ranges)):
        prev = all_block_ranges[i - 1]
        curr = all_block_ranges[i]

        if curr[0] <= prev[1]:
            fail(
                f"Validation: overlapping blocks "
                f"{prev[2]} and {curr[2]}."
            )

    # 11. Heldout sessions only in test_heldout.
    heldout_ids = {
        SPLITS["test_heldout"]
    }

    for s in HELDOUT:
        idx = np.flatnonzero(session == s)

        if len(idx) == 0:
            continue

        if not np.all(
            np.isin(split_id[idx], list(heldout_ids))
        ):
            fail(
                f"Validation: heldout session {s} "
                f"appears outside test_heldout."
            )

    # 12. No non-heldout session appears in test_heldout.
    idx = np.flatnonzero(
        split_id == SPLITS["test_heldout"]
    )

    nonheldout_sessions = set(session[idx]) - HELDOUT

    if nonheldout_sessions:
        fail(
            "Validation: non-heldout sessions found in "
            f"test_heldout: {sorted(nonheldout_sessions)}"
        )

    # 13. Split IDs valid.
    valid_split_ids = set(SPLITS.values())

    if not set(np.unique(split_id)).issubset(
        valid_split_ids
    ):
        fail("Validation: invalid split ID.")

    # 14. All seven categories represented.
    category_ids_present = set(
        np.unique(category_id).tolist()
    )

    expected_category_ids = set(
        label_mapping.values()
    )

    if category_ids_present != expected_category_ids:
        fail(
            "Validation: not all seven categories represented."
        )

    # 15. Full package cap validation.
    # Train/val/test_within caps are PER CATEGORY.
    # Held-out cap is PER HELD-OUT SESSION.
    if not pilot:

        category_names = {
            int(v): k
            for k, v in label_mapping.items()
        }

        for split, cap in CAPS.items():

            split_mask = split_id == SPLITS[split]

            for category_id_value in sorted(
                expected_category_ids
            ):

                n = int(
                    np.sum(
                        split_mask
                        & (category_id == category_id_value)
                    )
                )

                if n > cap:
                    category_name = category_names.get(
                        int(category_id_value),
                        str(category_id_value),
                    )

                    fail(
                        f"Validation: {split}/{category_name} "
                        f"cap exceeded: {n:,} > {cap:,}"
                    )

        for s in HELDOUT:
            n = int(
                np.sum(session == s)
            )

            if n > HELDOUT_SESSION_CAP:
                fail(
                    f"Validation: heldout cap exceeded "
                    f"for {s}: {n:,}"
                )

    # 16. Pilot must contain all four splits.
    if pilot:
        present_splits = set(
            np.unique(split_id).tolist()
        )

        if present_splits != set(SPLITS.values()):
            fail(
                "Validation: pilot does not contain all four splits. "
                f"Found {sorted(present_splits)}."
            )

    print("[OK] 38 features")
    print("[OK] FPT/LPT absent")
    print("[OK] float32")
    print("[OK] finite X")
    print("[OK] metadata aligned")
    print("[OK] unique row IDs")
    print("[OK] block minimum size")
    print("[OK] consecutive row IDs within blocks")
    print("[OK] session purity")
    print("[OK] split purity")
    print("[OK] category purity")
    print("[OK] no overlapping blocks")
    print("[OK] heldout-session isolation")
    print("[OK] category coverage")
    print("[OK] cap validation")

    if pilot:
        print("[OK] all four splits represented")

    return True


# ============================================================
# Pilot creation
# ============================================================
def create_pilot(
    full_dir,
    pilot_dir,
    blocks,
    features,
):
    """
    Select COMPLETE BLOCKS only.

    Pilot requirements:
      - all 7 categories represented
      - all 4 splits represented
      - no row-level truncation
      - every selected block remains intact
      - no duplicate blocks
      - deterministic selection
    """

    print("\n[8/9] Creating complete-block pilot...")

    required_splits = [
        "train",
        "val",
        "test_within",
        "test_heldout",
    ]

    required_categories = sorted(
        set(b["category"] for b in blocks)
    )

    if len(required_categories) != 7:
        fail(
            "Pilot creation expected 7 categories in the "
            f"selected full package, found {len(required_categories)}: "
            f"{required_categories}"
        )

    pilot_blocks = []
    chosen_ids = set()

    def add_block(block):
        bid = block["block_id"]

        if bid in chosen_ids:
            return False

        pilot_blocks.append(block)
        chosen_ids.add(bid)
        return True

    # --------------------------------------------------------
    # Phase 1: guarantee all seven categories.
    #
    # Prefer a block whose split is not yet represented.
    # This simultaneously helps satisfy the split requirement.
    # --------------------------------------------------------
    represented_splits = set()

    for category in required_categories:

        options = [
            b for b in blocks
            if (
                b["category"] == category
                and b["block_id"] not in chosen_ids
            )
        ]

        if not options:
            fail(
                f"No full-package block available for pilot "
                f"category {category}."
            )

        # Prefer an option introducing a new split.
        new_split_options = [
            b for b in options
            if b["split"] not in represented_splits
        ]

        if new_split_options:
            options = new_split_options

        # Deterministic canonical-order selection.
        options.sort(
            key=lambda b: (
                b["start"],
                b["block_id"],
            )
        )

        chosen = options[0]
        add_block(chosen)
        represented_splits.add(chosen["split"])

    # --------------------------------------------------------
    # Phase 2: explicitly guarantee all four splits.
    # --------------------------------------------------------
    for split in required_splits:

        if split in represented_splits:
            continue

        options = [
            b for b in blocks
            if (
                b["split"] == split
                and b["block_id"] not in chosen_ids
            )
        ]

        if not options:
            fail(
                f"No full-package block available for pilot "
                f"split {split}."
            )

        options.sort(
            key=lambda b: (
                b["start"],
                b["block_id"],
            )
        )

        chosen = options[0]
        add_block(chosen)
        represented_splits.add(chosen["split"])

    # --------------------------------------------------------
    # Phase 3: fill toward the pilot target using COMPLETE
    # blocks only.
    #
    # We intentionally do not slice/truncate a block.
    # Therefore the final pilot may be slightly above
    # PILOT_TARGET.
    # --------------------------------------------------------
    pilot_rows = sum(
        b["nrows"]
        for b in pilot_blocks
    )

    for b in blocks:

        if pilot_rows >= PILOT_TARGET:
            break

        if b["block_id"] in chosen_ids:
            continue

        add_block(b)
        pilot_rows += b["nrows"]

    # Canonical row order.
    pilot_blocks.sort(
        key=lambda x: (
            x["start"],
            x["block_id"],
        )
    )

    pilot_rows = sum(
        b["nrows"]
        for b in pilot_blocks
    )

    # --------------------------------------------------------
    # Defensive checks BEFORE writing the pilot.
    # --------------------------------------------------------
    final_categories = {
        b["category"]
        for b in pilot_blocks
    }

    final_splits = {
        b["split"]
        for b in pilot_blocks
    }

    if final_categories != set(required_categories):
        fail(
            "Pilot construction failed category coverage. "
            f"Expected {required_categories}, "
            f"found {sorted(final_categories)}."
        )

    if final_splits != set(required_splits):
        fail(
            "Pilot construction failed split coverage. "
            f"Expected {required_splits}, "
            f"found {sorted(final_splits)}."
        )

    # Ensure block IDs are unique.
    if len(chosen_ids) != len(pilot_blocks):
        fail(
            "Pilot construction produced duplicate block IDs."
        )

    # Ensure every block is complete and valid.
    for b in pilot_blocks:

        if b["nrows"] < MIN_BLOCK:
            fail(
                f"Pilot contains block {b['block_id']} "
                f"with only {b['nrows']} rows."
            )

        if b["end"] - b["start"] != b["nrows"]:
            fail(
                f"Pilot block {b['block_id']} is not a complete "
                "canonical interval."
            )

    if pilot_rows < PILOT_TARGET:
        print(
            f"[INFO] Pilot target {PILOT_TARGET:,} cannot be reached "
            f"without splitting a block."
        )

    print(f"[OK] Pilot blocks: {len(pilot_blocks):,}")
    print(f"[OK] Pilot rows  : {pilot_rows:,}")
    print("[OK] Pilot uses complete blocks only.")
    print(
        "[OK] Pilot categories: "
        + ", ".join(sorted(final_categories))
    )
    print(
        "[OK] Pilot splits: "
        + ", ".join(required_splits)
    )

    # --------------------------------------------------------
    # Load full arrays.
    # --------------------------------------------------------
    X_full = np.load(
        full_dir / "mu_iot_features_38_float32.npy",
        mmap_mode="r",
    )

    meta_full = np.load(
        full_dir / "mu_iot_meta.npz",
        allow_pickle=False,
    )

    pilot_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    X_pilot = np.lib.format.open_memmap(
        pilot_dir / "mu_iot_features_38_float32.npy",
        mode="w+",
        dtype=np.float32,
        shape=(pilot_rows, len(features)),
    )

    meta_arrays = {
        key: np.empty(
            pilot_rows,
            dtype=meta_full[key].dtype,
        )
        for key in META_COLUMNS
    }

    out_pos = 0

    # Full package block IDs are unique.
    for b in pilot_blocks:

        bid = b["block_id"]

        idx = np.flatnonzero(
            meta_full["block_id"] == bid
        )

        if len(idx) != b["nrows"]:
            fail(
                f"Pilot: block {bid} row count mismatch."
            )

        n = len(idx)

        X_pilot[
            out_pos:out_pos + n
        ] = X_full[idx]

        for key in META_COLUMNS:
            meta_arrays[key][
                out_pos:out_pos + n
            ] = meta_full[key][idx]

        out_pos += n

    if out_pos != pilot_rows:
        fail(
            f"Pilot output row mismatch: wrote {out_pos:,}, "
            f"expected {pilot_rows:,}."
        )

    X_pilot.flush()
    del X_pilot

    np.savez_compressed(
        pilot_dir / "mu_iot_meta.npz",
        **meta_arrays,
    )

    (pilot_dir / "feature_list_38.json").write_text(
        json.dumps(
            features,
            indent=2,
        ),
        encoding="utf-8",
    )

    (pilot_dir / "label_mapping.json").write_text(
        json.dumps(
            json.loads(
                (full_dir / "label_mapping.json").read_text(
                    encoding="utf-8"
                )
            ),
            indent=2,
        ),
        encoding="utf-8",
    )

    shutil.copy2(
        full_dir / "scaler_38.pkl",
        pilot_dir / "scaler_38.pkl",
    )

    # Manifest containing only pilot blocks.
    write_manifest(
        pilot_blocks,
        pilot_dir / "block_manifest.csv",
    )

    return pilot_rows


# ============================================================
# README
# ============================================================

def write_readme(
    build_dir,
    features,
    scaler_rows,
    full_rows,
    pilot_rows,
):
    text = f"""# MU-IoT Handoff V3

Generated from the canonical cleaned master:

`{CLEANED}`

## Feature set

Existing feature key:

`{BASE_KEY}`

Existing feature count:

40

Removed:

- FPT
- LPT

Final feature key:

`{NEW_KEY}`

Final feature count:

38

## Canonical row ID

`row_id` is the zero-based physical row position in the cleaned master CSV.

Range:

`0 ... 24,171,262`

## Source-of-truth rule

V3 does NOT use the original raw CSV files for row identity.

All selected data comes from:

`mu_iot_cleaned.csv`

## Splits

Held-out sessions:

- MU_SESSION_013
- MU_SESSION_021
- MU_SESSION_026
- MU_SESSION_031

Held-out sessions are exclusively `test_heldout`.

Other sessions use chronological session-local:

- 70% train
- 15% val
- 15% test_within

## Complete blocks

Block size:

{BLOCK_SIZE:,}

Minimum block size:

{MIN_BLOCK}

No partial block is allowed.

## Caps

Train:

{CAPS["train"]:,}

Validation:

{CAPS["val"]:,}

Within-session test:

{CAPS["test_within"]:,}

Each held-out session:

{HELDOUT_SESSION_CAP:,}

## Scaling

`StandardScaler` is fitted only on selected TRAIN rows.

Train rows used for scaler fitting:

{scaler_rows:,}

## Output

Full rows:

{full_rows:,}

Pilot rows:

{pilot_rows:,}

X dtype:

float32

Pilot construction uses complete blocks only. There is no row-level pilot truncation.

## Validation

V3 validates:

1. exactly 38 features
2. FPT/LPT absent
3. canonical row IDs
4. unique row IDs
5. complete blocks
6. consecutive row IDs within blocks
7. no overlapping blocks
8. session purity
9. split purity
10. category purity
11. held-out session isolation
12. split/category coverage
13. caps
14. float32
15. finite transformed data
16. metadata/X alignment
17. train-only scaler fitting
"""

    (build_dir / "README.md").write_text(
        text,
        encoding="utf-8",
    )


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 72)
    print("MU-IoT HANDOFF V3 - CLEANED MASTER BUILDER")
    print("=" * 72)

    features = load_features()

    inspect_header(features)

    session_regions, total_rows = discover_sessions()

    split_regions = assign_split_regions(
        session_regions
    )

    candidates = create_candidate_blocks(
        split_regions
    )

    selected = select_blocks(
        candidates
    )

    build_dir = OUT / "_build_tmp"

    if build_dir.exists():
        shutil.rmtree(build_dir)

    build_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_manifest(
        selected,
        build_dir / "block_manifest.csv",
    )

    label_mapping = build_label_mapping(
        selected
    )

    (build_dir / "session_regions.json").write_text(
        json.dumps(
            session_regions,
            indent=2,
        ),
        encoding="utf-8",
    )

    (build_dir / "split_regions.json").write_text(
        json.dumps(
            split_regions,
            indent=2,
        ),
        encoding="utf-8",
    )

    scaler, scaler_rows = fit_train_scaler(
        selected,
        features,
    )

    full_rows = write_full_package(
        selected,
        features,
        scaler,
        label_mapping,
        build_dir,
    )

    write_counts(
        selected,
        label_mapping,
        build_dir / "class_counts_by_split.csv",
    )

    validate_package(
        build_dir,
        selected,
        features,
        label_mapping,
        full_rows,
        pilot=False,
    )

    # --------------------------------------------------------
    # Create pilot from complete blocks.
    # --------------------------------------------------------

    pilot_dir = build_dir / "pilot"

    pilot_rows = create_pilot(
        build_dir,
        pilot_dir,
        selected,
        features,
    )

    validate_package(
        pilot_dir,
        [
            b for b in selected
            if b["block_id"] in set(
                pd.read_csv(
                    pilot_dir / "block_manifest.csv"
                )["block_id"].tolist()
            )
        ],
        features,
        label_mapping,
        pilot_rows,
        pilot=True,
    )

    write_readme(
        build_dir,
        features,
        scaler_rows,
        full_rows,
        pilot_rows,
    )

    # --------------------------------------------------------
    # Final atomic replacement.
    # --------------------------------------------------------

    final_dir = OUT

    # Preserve old final output if it exists.
    old_dir = None

    if final_dir.exists():

        old_dir = (
            final_dir.parent
            / (
                final_dir.name
                + "_before_rebuild"
            )
        )

        if old_dir.exists():
            shutil.rmtree(old_dir)

        # Move everything except _build_tmp.
        for item in list(final_dir.iterdir()):
            if item.name == "_build_tmp":
                continue

            target = old_dir / item.name
            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            shutil.move(
                str(item),
                str(target),
            )

    # Move build contents into final output.
    for item in list(build_dir.iterdir()):

        if item.name == "pilot":
            target = final_dir / "pilot"
        else:
            target = final_dir / item.name

        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        shutil.move(
            str(item),
            str(target),
        )

    if build_dir.exists():
        try:
            build_dir.rmdir()
        except OSError:
            pass

    print("\n" + "=" * 72)
    print("V3 BUILD COMPLETE")
    print("=" * 72)

    print(f"Output : {OUT}")
    print(f"Full rows   : {full_rows:,}")
    print(f"Pilot rows  : {pilot_rows:,}")
    print(f"Train scaler rows: {scaler_rows:,}")
    print("Features    : 38")
    print("FPT/LPT     : removed")
    print("Source      : cleaned master")
    print("Validation  : PASSED")


if __name__ == "__main__":
    main()
