from pathlib import Path
import pandas as pd

BOUNDARY_FILE = Path(
    r"D:\Major_Project\output\mu_iot\mu_iot_boundary_decisions.csv"
)

OUTPUT_FILE = Path(
    r"D:\Major_Project\output\mu_iot\mu_iot_capture_sessions.csv"
)

df = pd.read_csv(BOUNDARY_FILE)

# Start a new session whenever the previous file
# is not marked CONTINUOUS.
#
# We process the rows in the same order as the
# boundary report.

session_number = 1
session_map = {}

for _, row in df.iterrows():

    filepath = row["relative_path"]

    if filepath not in session_map:
        session_map[filepath] = f"MU_SESSION_{session_number:03d}"

    if row["decision"] == "SEPARATE_SESSION":
        session_number += 1

        next_path = row["next_relative_path"]

        if next_path:
            session_map[next_path] = (
                f"MU_SESSION_{session_number:03d}"
            )

    elif row["decision"] == "NO_SUCCESSOR":
        session_number += 1


# Build final mapping
records = []

for _, row in df.iterrows():

    filepath = row["relative_path"]

    records.append(
        {
            "relative_path": filepath,
            "filename": row["filename"],
            "group": row["group"],
            "capture_session": session_map[filepath],
        }
    )

result = pd.DataFrame(records)

# Remove accidental duplicates
result = result.drop_duplicates(
    subset=["relative_path"]
)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

result.to_csv(
    OUTPUT_FILE,
    index=False
)

print("=" * 70)
print("CAPTURE SESSION MAPPING CREATED")
print("=" * 70)

print(f"Files mapped    : {len(result)}")
print(f"Sessions created: {result['capture_session'].nunique()}")
print(f"Output          : {OUTPUT_FILE}")

print()
print("Session mapping:")
print(
    result[
        [
            "filename",
            "capture_session"
        ]
    ].to_string(index=False)
)