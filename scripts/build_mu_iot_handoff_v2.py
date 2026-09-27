from pathlib import Path
import pandas as pd
import numpy as np
import json
import re
import shutil

ROOT = Path(r"D:\Major_Project")

RAW = ROOT / r"dataset\mu_iot\CSV"
OUT = ROOT / r"dataset\processed\mu_iot\handoff_v2"
CFG = ROOT / r"config\mu_iot_feature_sets.json"
MAP = ROOT / r"output\mu_iot\mu_iot_capture_sessions_v2.csv"

CHUNK = 100_000
PART_TARGET = 500_000

NORMAL_CAP = 1_000_000
TYPE_CAP = 250_000

PILOT_N = 200_000


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def norm(x):
    return re.sub(r"[^a-z0-9]", "", str(x).lower())


def pick(cols, names):
    mapping = {norm(c): c for c in cols}

    for name in names:
        key = norm(name)
        if key in mapping:
            return mapping[key]

    return None


def load_features():
    cfg = json.loads(
        CFG.read_text(encoding="utf-8")
    )

    features = (
        cfg.get("paper_top48")
        or cfg.get("table8_available_features")
    )

    metadata = {
        "FPT",
        "LPT",
        "capture_session",
        "source_file",
        "orig_row",
        "source_ip",
        "destination_ip",
        "source_port",
        "destination_port",
        "protocol",
        "service",
        "label",
        "label_id",
        "category",
        "category_id",
        "type",
        "type_id",
    }

    return [
        c for c in features
        if c not in metadata
    ]


def find_raw_files():
    files = sorted(
        RAW.rglob("*.csv")
    )

    return files


# ------------------------------------------------------------
# Session map
# ------------------------------------------------------------

def load_session_map():
    sm = pd.read_csv(MAP)

    required = {
        "relative_path",
        "filename",
        "capture_session",
    }

    missing = required - set(sm.columns)

    if missing:
        raise RuntimeError(
            f"Session map missing columns: {sorted(missing)}"
        )

    lookup = {}

    for _, row in sm.iterrows():

        rel = str(
            row["relative_path"]
        ).replace("/", "\\")

        lookup[rel.lower()] = str(
            row["capture_session"]
        )

        filename = str(
            row["filename"]
        )

        lookup[
            filename.lower()
        ] = str(
            row["capture_session"]
        )

    return sm, lookup


def get_session(raw_file, lookup):
    rel = str(
        raw_file.relative_to(RAW)
    ).replace("/", "\\")

    if rel.lower() in lookup:
        return lookup[rel.lower()]

    name = raw_file.name.lower()

    if name in lookup:
        return lookup[name]

    raise RuntimeError(
        f"No capture session mapping found for:\n{rel}"
    )


# ------------------------------------------------------------
# Schema
# ------------------------------------------------------------

def detect_schema(columns):
    return {
        "category": pick(
            columns,
            ["category"]
        ),
        "type": pick(
            columns,
            ["type", "attack_type", "class"]
        ),
        "label": pick(
            columns,
            ["label", "attack_label", "attack"]
        ),
        "FPT": pick(
            columns,
            ["FPT"]
        ),
        "LPT": pick(
            columns,
            ["LPT"]
        ),
        "source_ip": pick(
            columns,
            ["source_ip", "src_ip", "SIP"]
        ),
        "destination_ip": pick(
            columns,
            ["destination_ip", "dest_ip", "DIP"]
        ),
        "source_port": pick(
            columns,
            ["source_port", "src_port", "SPort"]
        ),
        "destination_port": pick(
            columns,
            ["destination_port", "dest_port", "DPort"]
        ),
        "protocol": pick(
            columns,
            ["protocol", "proto", "Proto"]
        ),
        "service": pick(
            columns,
            ["service"]
        ),
    }


# ------------------------------------------------------------
# PASS 1
# Count rows by file/type/category
# ------------------------------------------------------------

def inspect_files(files, session_lookup):

    print()
    print("=" * 70)
    print("PASS 1 — INSPECTING RAW MU-IoT FILES")
    print("=" * 70)

    records = []

    for number, path in enumerate(files, 1):

        print(
            f"[{number:02d}/{len(files):02d}] "
            f"{path.name}"
        )

        header = pd.read_csv(
            path,
            nrows=0
        )

        schema = detect_schema(
            header.columns
        )

        if not schema["type"]:
            raise RuntimeError(
                f"No type column in {path}"
            )

        if not schema["category"]:
            raise RuntimeError(
                f"No category column in {path}"
            )

        usecols = [
            schema["category"],
            schema["type"],
        ]

        # Avoid duplicate usecols.
        usecols = list(
            dict.fromkeys(
                usecols
            )
        )

        counts = {}

        for chunk in pd.read_csv(
            path,
            usecols=usecols,
            chunksize=CHUNK,
            low_memory=False
        ):

            category = (
                chunk[
                    schema["category"]
                ]
                .fillna("unknown")
                .astype(str)
            )

            typ = (
                chunk[
                    schema["type"]
                ]
                .fillna("unknown")
                .astype(str)
            )

            tmp = pd.DataFrame({
                "category": category,
                "type": typ
            })

            grouped = (
                tmp
                .groupby(
                    ["category", "type"],
                    dropna=False
                )
                .size()
            )

            for key, value in grouped.items():

                counts[key] = (
                    counts.get(key, 0)
                    + int(value)
                )

        session = get_session(
            path,
            session_lookup
        )

        for (category, typ), count in counts.items():

            records.append({
                "path": str(path),
                "relative_path": str(
                    path.relative_to(RAW)
                ).replace("/", "\\"),
                "filename": path.name,
                "capture_session": session,
                "category": category,
                "type": typ,
                "rows": count,
            })

    audit = pd.DataFrame(records)

    audit.to_csv(
        OUT / "source_type_audit.csv",
        index=False
    )

    return audit


# ------------------------------------------------------------
# Build quotas
# ------------------------------------------------------------

def build_quotas(audit):

    print()
    print("=" * 70)
    print("BUILDING TYPE QUOTAS")
    print("=" * 70)

    type_totals = (
        audit
        .groupby(
            "type",
            as_index=False
        )["rows"]
        .sum()
    )

    quotas = {}

    for _, row in type_totals.iterrows():

        typ = str(
            row["type"]
        )

        total = int(
            row["rows"]
        )

        if typ.lower() == "normal":
            cap = min(
                total,
                NORMAL_CAP
            )
        else:
            cap = min(
                total,
                TYPE_CAP
            )

        quotas[typ] = cap

        print(
            f"{typ:25s} "
            f"available={total:10,d} "
            f"quota={cap:10,d}"
        )

    return quotas


# ------------------------------------------------------------
# Allocate quotas across files
# ------------------------------------------------------------

def allocate_file_quotas(audit, quotas):

    result = audit.copy()

    result["quota"] = 0

    for typ, total_quota in quotas.items():

        mask = (
            result["type"].astype(str)
            == str(typ)
        )

        subset = result.loc[
            mask
        ].copy()

        available = int(
            subset["rows"].sum()
        )

        if available == 0:
            continue

        remaining = total_quota

        # Allocate proportionally, while ensuring
        # small source files are not automatically lost.
        allocations = []

        for _, row in subset.iterrows():

            proportion = (
                int(row["rows"])
                / available
            )

            allocation = int(
                total_quota
                * proportion
            )

            allocation = min(
                allocation,
                int(row["rows"])
            )

            allocations.append(
                allocation
            )

        allocated = sum(
            allocations
        )

        # Distribute remaining rows in source order.
        deficit = total_quota - allocated

        for i in range(
            len(allocations)
        ):

            if deficit <= 0:
                break

            idx = subset.index[i]

            room = (
                int(result.loc[idx, "rows"])
                - allocations[i]
            )

            add = min(
                room,
                deficit
            )

            allocations[i] += add
            deficit -= add

        for idx, allocation in zip(
            subset.index,
            allocations
        ):
            result.loc[
                idx,
                "quota"
            ] = allocation

    result.to_csv(
        OUT / "source_quota_plan.csv",
        index=False
    )

    return result


# ------------------------------------------------------------
# Read selected contiguous blocks
# ------------------------------------------------------------

def build_selected_stream(
    quota_plan,
    feature_cols,
    session_lookup
):

    print()
    print("=" * 70)
    print("PASS 2 — BUILDING CONTIGUOUS HANDOFF")
    print("=" * 70)

    temp_dir = OUT / "_temp"
    temp_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_csv = (
        temp_dir
        / "selected.csv"
    )

    if temp_csv.exists():
        temp_csv.unlink()

    first_write = True

    for number, row in enumerate(
        quota_plan.itertuples(index=False),
        1
    ):

        quota = int(
            row.quota
        )

        if quota <= 0:
            continue

        path = Path(
            row.path
        )

        print(
            f"[{number:02d}] "
            f"{path.name} "
            f"quota={quota:,}"
        )

        header = pd.read_csv(
            path,
            nrows=0
        )

        schema = detect_schema(
            header.columns
        )

        needed_source = list(
            dict.fromkeys(
                [
                    c
                    for c in [
                        schema["category"],
                        schema["type"],
                        schema["label"],
                        schema["FPT"],
                        schema["LPT"],
                        schema["source_ip"],
                        schema["destination_ip"],
                        schema["source_port"],
                        schema["destination_port"],
                        schema["protocol"],
                        schema["service"],
                    ]
                    if c is not None
                ]
                + feature_cols
            )
        )

        available = [
            c
            for c in needed_source
            if c in header.columns
        ]

        chunks = []

        remaining = quota
        orig_offset = 0

        # Read only the contiguous prefix required from
        # this source file.
        for chunk in pd.read_csv(
            path,
            usecols=available,
            chunksize=CHUNK,
            low_memory=False
        ):

            if remaining <= 0:
                break

            take = min(
                len(chunk),
                remaining
            )

            chunk = chunk.iloc[
                :take
            ].copy()

            # Keep source order.
            chunk["orig_row"] = np.arange(
                orig_offset,
                orig_offset + len(chunk),
                dtype=np.int64
            )

            orig_offset += len(chunk)
            remaining -= len(chunk)

            # Canonical names.
            rename = {}

            for canonical, actual in schema.items():

                if actual is not None:
                    rename[actual] = canonical

            chunk.rename(
                columns=rename,
                inplace=True
            )

            # Required labels.
            for c in [
                "label",
                "category",
                "type"
            ]:

                if c not in chunk.columns:
                    chunk[c] = "unknown"

                chunk[c] = (
                    chunk[c]
                    .fillna("unknown")
                    .astype(str)
                )

            original_session = str(
                row.capture_session
            )

            # This file is one contiguous block in this
            # handoff. If it is ever split in future,
            # the block number can be appended here.
            chunk["capture_session"] = (
                original_session
            )

            chunk["source_file"] = (
                path.name
            )

            chunks.append(
                chunk
            )

        if not chunks:
            continue

        selected = pd.concat(
            chunks,
            ignore_index=True
        )

        ordered_meta = [
            "capture_session",
            "source_file",
            "orig_row",
            "FPT",
            "LPT",
            "source_ip",
            "destination_ip",
            "source_port",
            "destination_port",
            "protocol",
            "service",
        ]

        ordered_labels = [
            "label",
            "category",
            "type",
        ]

        final = [
            c
            for c in (
                ordered_meta
                + ordered_labels
                + feature_cols
            )
            if c in selected.columns
        ]

        selected = selected[
            final
        ]

        selected.to_csv(
            temp_csv,
            mode="a",
            header=first_write,
            index=False
        )

        first_write = False

        print(
            f"    selected={len(selected):,}"
        )

    return temp_csv


# ------------------------------------------------------------
# Convert selected CSV to Parquet
# ------------------------------------------------------------

def convert_to_parquet(
    temp_csv,
    feature_cols
):

    print()
    print("=" * 70)
    print("PASS 3 — PARQUET CONVERSION")
    print("=" * 70)

    full_dir = OUT / "full"
    pilot_dir = OUT / "pilot"

    full_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    pilot_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    for old in full_dir.glob(
        "*.parquet"
    ):
        old.unlink()

    for old in pilot_dir.glob(
        "*.parquet"
    ):
        old.unlink()

    # Determine global mappings first.
    print("Building label mappings...")

    label_sets = {
        "label": set(),
        "category": set(),
        "type": set()
    }

    for chunk in pd.read_csv(
        temp_csv,
        usecols=[
            "label",
            "category",
            "type"
        ],
        chunksize=CHUNK,
        low_memory=False
    ):

        for c in label_sets:
            label_sets[c].update(
                chunk[c]
                .fillna("unknown")
                .astype(str)
                .unique()
            )

    mappings = {}

    for c in label_sets:

        values = sorted(
            label_sets[c]
        )

        mappings[c] = {
            value: i
            for i, value in enumerate(values)
        }

    # Calculate feature medians.
    print("Calculating feature medians...")

    median_values = {}

    median_data = {
        c: []
        for c in feature_cols
    }

    for chunk in pd.read_csv(
        temp_csv,
        usecols=feature_cols,
        chunksize=CHUNK,
        low_memory=False
    ):

        for c in feature_cols:

            s = pd.to_numeric(
                chunk[c],
                errors="coerce"
            )

            s = s.mask(
                ~np.isfinite(s),
                np.nan
            )

            median_data[c].append(
                s
            )

    for c in feature_cols:

        combined = pd.concat(
            median_data[c],
            ignore_index=True
        )

        median_values[c] = (
            combined.median()
        )

        del combined

    # Second pass — write Parquet.
    part_number = 1
    total = 0

    stats = {
        c: []
        for c in feature_cols
    }

    session_rows = {}

    class_counts = {}

    pilot_buffer = []

    buffer = []

    def clean_chunk(chunk):

        for c in feature_cols:

            s = pd.to_numeric(
                chunk[c],
                errors="coerce"
            )

            s = s.mask(
                ~np.isfinite(s),
                np.nan
            )

            median = median_values[c]

            if pd.isna(median):
                median = 0.0

            chunk[c] = (
                s.fillna(median)
                .astype("float32")
            )

        for c in [
            "label",
            "category",
            "type"
        ]:

            chunk[c] = (
                chunk[c]
                .fillna("unknown")
                .astype(str)
            )

            chunk[
                c + "_id"
            ] = (
                chunk[c]
                .map(mappings[c])
                .astype("int32")
            )

        chunk["capture_session"] = (
            chunk["capture_session"]
            .astype(str)
        )

        chunk["source_file"] = (
            chunk["source_file"]
            .astype(str)
        )

        chunk["orig_row"] = (
            chunk["orig_row"]
            .astype("int64")
        )

        return chunk

    for chunk in pd.read_csv(
        temp_csv,
        chunksize=CHUNK,
        low_memory=False
    ):

        chunk = clean_chunk(
            chunk
        )

        total += len(chunk)

        # Pilot is exactly the first 200K
        # rows of the same contiguous stream.
        if len(pilot_buffer) < PILOT_N:

            needed = (
                PILOT_N
                - sum(
                    len(x)
                    for x in pilot_buffer
                )
            )

            pilot_buffer.append(
                chunk.iloc[
                    :needed
                ].copy()
            )

        buffer.append(
            chunk
        )

        current = sum(
            len(x)
            for x in buffer
        )

        if current >= PART_TARGET:

            out = pd.concat(
                buffer,
                ignore_index=True
            )

            filename = (
                full_dir
                / (
                    f"mu_iot_processed_part_"
                    f"{part_number:03d}.parquet"
                )
            )

            out.to_parquet(
                filename,
                index=False,
                engine="pyarrow"
            )

            print(
                f"  wrote {filename.name}: "
                f"{len(out):,} rows"
            )

            for c in feature_cols:

                s = out[c].astype(float)

                stats[c].append({
                    "min": float(s.min()),
                    "max": float(s.max()),
                    "mean": float(s.mean()),
                    "std": float(s.std()),
                    "zero_pct": float(
                        (s == 0).mean()
                        * 100
                    )
                })

            for category, count in (
                out["category"]
                .value_counts()
                .items()
            ):

                class_counts[category] = (
                    class_counts.get(
                        category,
                        0
                    )
                    + int(count)
                )

            for session, count in (
                out[
                    "capture_session"
                ]
                .value_counts()
                .items()
            ):

                session_rows[session] = (
                    session_rows.get(
                        session,
                        0
                    )
                    + int(count)
                )

            buffer = []
            part_number += 1

    if buffer:

        out = pd.concat(
            buffer,
            ignore_index=True
        )

        filename = (
            full_dir
            / (
                f"mu_iot_processed_part_"
                f"{part_number:03d}.parquet"
            )
        )

        out.to_parquet(
            filename,
            index=False,
            engine="pyarrow"
        )

        print(
            f"  wrote {filename.name}: "
            f"{len(out):,} rows"
        )

        for category, count in (
            out["category"]
            .value_counts()
            .items()
        ):

            class_counts[category] = (
                class_counts.get(
                    category,
                    0
                )
                + int(count)
            )

        for session, count in (
            out[
                "capture_session"
            ]
            .value_counts()
            .items()
        ):

            session_rows[session] = (
                session_rows.get(
                    session,
                    0
                )
                + int(count)
            )

    # Pilot
    pilot = pd.concat(
        pilot_buffer,
        ignore_index=True
    ).iloc[
        :PILOT_N
    ]

    pilot.to_parquet(
        pilot_dir
        / "mu_iot_processed_pilot.parquet",
        index=False,
        engine="pyarrow"
    )

    # Support files
    feature_rows = []

    for c in feature_cols:

        if not stats[c]:
            continue

        values = stats[c]

        feature_rows.append({
            "feature": c,
            "min": min(
                x["min"]
                for x in values
            ),
            "max": max(
                x["max"]
                for x in values
            ),
            "mean": np.mean([
                x["mean"]
                for x in values
            ]),
            "std": np.mean([
                x["std"]
                for x in values
            ]),
            "zero_pct": np.mean([
                x["zero_pct"]
                for x in values
            ])
        })

    pd.DataFrame(
        feature_rows
    ).to_csv(
        OUT / "feature_stats.csv",
        index=False
    )

    pd.DataFrame(
        [
            {
                "capture_session": k,
                "rows": v
            }
            for k, v in session_rows.items()
        ]
    ).to_csv(
        OUT / "session_summary.csv",
        index=False
    )

    pd.DataFrame(
        [
            {
                "category": k,
                "rows": v
            }
            for k, v in class_counts.items()
        ]
    ).to_csv(
        OUT / "class_counts.csv",
        index=False
    )

    (
        OUT / "label_mappings.json"
    ).write_text(
        json.dumps(
            mappings,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    (
        OUT / "column_groups.json"
    ).write_text(
        json.dumps(
            {
                "model_features": feature_cols,
                "metadata": [
                    "capture_session",
                    "source_file",
                    "orig_row",
                    "FPT",
                    "LPT",
                    "source_ip",
                    "destination_ip",
                    "source_port",
                    "destination_port",
                    "protocol",
                    "service"
                ],
                "labels": [
                    "label",
                    "label_id",
                    "category",
                    "category_id",
                    "type",
                    "type_id"
                ]
            },
            indent=2
        ),
        encoding="utf-8"
    )

    readme = f"""# MU-IoT Final Model Handoff

Generated: {pd.Timestamp.now().isoformat()}

## Dataset

Source:
{RAW}

Selected rows:
{total:,}

Pilot:
{PILOT_N:,}

## Model features

Number of model features:
{len(feature_cols)}

The features follow the configured paper-ranked feature list,
excluding FPT/LPT and other metadata fields.

## Metadata

Preserved:

- capture_session
- source_file
- orig_row
- FPT
- LPT
- source_ip
- destination_ip
- source_port
- destination_port
- protocol
- service

## Labels

Preserved:

- label
- label_id
- category
- category_id
- type
- type_id

## Cleaning

- Numeric conversion performed.
- Positive/negative infinity converted to NaN.
- NaN values median-imputed.
- Float features stored as float32.
- No scaling.
- No log transform.
- No train/test split.
- Duplicate rows were not intentionally removed.
- Original source order preserved.

## Sampling

- Sampling is contiguous within each source file.
- No random row sampling.
- Attack types capped at approximately {TYPE_CAP:,} rows.
- Normal capped at approximately {NORMAL_CAP:,} rows.
- Capture-session identity preserved.
"""

    (
        OUT / "README.md"
    ).write_text(
        readme,
        encoding="utf-8"
    )

    print()
    print("=" * 70)
    print("FINAL HANDOFF COMPLETE")
    print("=" * 70)
    print(f"TOTAL ROWS: {total:,}")
    print(f"PILOT ROWS: {PILOT_N:,}")
    print(f"OUTPUT: {OUT}")
    print("=" * 70)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    print("=" * 70)
    print("MU-IoT FINAL HANDOFF BUILDER V2")
    print("=" * 70)

    feature_cols = load_features()

    print(
        f"Model features: {len(feature_cols)}"
    )

    print(
        ", ".join(feature_cols)
    )

    files = find_raw_files()

    print(
        f"\nRaw CSV files found: {len(files)}"
    )

    if len(files) != 40:
        print(
            "WARNING: expected approximately 40 files."
        )

    OUT.mkdir(
        parents=True,
        exist_ok=True
    )

    session_map, session_lookup = (
        load_session_map()
    )

    print(
        f"Session-map entries: "
        f"{len(session_map)}"
    )

    audit = inspect_files(
        files,
        session_lookup
    )

    quotas = build_quotas(
        audit
    )

    quota_plan = allocate_file_quotas(
        audit,
        quotas
    )

    total_quota = int(
        quota_plan["quota"].sum()
    )

    print()
    print(
        f"TOTAL PLANNED ROWS: "
        f"{total_quota:,}"
    )

    temp_csv = build_selected_stream(
        quota_plan,
        feature_cols,
        session_lookup
    )

    convert_to_parquet(
        temp_csv,
        feature_cols
    )

    print()
    print(
        "Temporary selected CSV retained at:"
    )
    print(temp_csv)


if __name__ == "__main__":
    main()