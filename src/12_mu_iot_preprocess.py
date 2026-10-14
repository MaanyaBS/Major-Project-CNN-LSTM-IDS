from pathlib import Path
import pandas as pd
import numpy as np
import ipaddress

# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(r"D:\Major_Project\dataset\mu_iot\CSV")

SESSION_FILE = Path(
    r"D:\Major_Project\output\mu_iot\mu_iot_capture_sessions.csv"
)

OUTPUT_DIR = Path(
    r"D:\Major_Project\dataset\processed\mu_iot"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "mu_iot_cleaned.csv"

CHUNK_SIZE = 100_000

TARGET = "category"

# ============================================================
# COLUMNS TO REMOVE
# ============================================================

DROP_COLUMNS = [
    # Completely empty columns
    "HTTPDeletC",
    "HTTPPatchC",
    "HTTPTraceC",
    "HTTPConC",
    "RTSP_SPC",
    "RTSP_RecordC",
    "RTSP_RedirectC",
    "RTSP_PauseC",

    # Constant columns
    "CE",
    "HTTPHeadC",
    "MQTT_MTM",
    "RTSP_OptionC",
    "RTSP_DESCC",
    "RTSP_TeardownC",
    "RTSP_PlayC",

    # Target leakage / unwanted labels
    "label",
    "type",
]

# ============================================================
# CATEGORICAL ENCODINGS
# ============================================================

HTTP_MAPPING = {
    "GET": 0,
    "POST": 1,
    "OPTIONS": 2,
    "HEAD": 3,
    "PUT": 4,
    "DELETE": 5,
}

RTSP_MAPPING = {
    "GET_PARAMETER": 0,
    "SETUP": 1,
    "OPTIONS": 2,
    "TEARDOWN": 3,
    "DESCRIBE": 4,
    "PLAY": 5,
}


# ============================================================
# IP FEATURE EXTRACTION
# ============================================================

def extract_ip_features(series, prefix):

    private = []
    loopback = []
    multicast = []
    link_local = []
    first_octet = []
    last_octet = []

    for value in series:

        try:

            value = str(value).strip()
            ip = ipaddress.ip_address(value)

            parts = str(ip).split(".")

            private.append(int(ip.is_private))
            loopback.append(int(ip.is_loopback))
            multicast.append(int(ip.is_multicast))
            link_local.append(int(ip.is_link_local))

            first_octet.append(int(parts[0]))
            last_octet.append(int(parts[-1]))

        except Exception:

            private.append(0)
            loopback.append(0)
            multicast.append(0)
            link_local.append(0)

            first_octet.append(-1)
            last_octet.append(-1)

    return pd.DataFrame({
        f"{prefix}_private": private,
        f"{prefix}_loopback": loopback,
        f"{prefix}_multicast": multicast,
        f"{prefix}_link_local": link_local,
        f"{prefix}_first_octet": first_octet,
        f"{prefix}_last_octet": last_octet,
    }, index=series.index)


# ============================================================
# LOAD SESSION MAPPING
# ============================================================

def load_session_mapping():

    session_df = pd.read_csv(SESSION_FILE)

    required = {
        "relative_path",
        "filename",
        "capture_session"
    }

    missing = required - set(session_df.columns)

    if missing:
        raise ValueError(
            f"Session mapping missing columns: {missing}"
        )

    mapping = {}

    for _, row in session_df.iterrows():

        relative_path = str(
            row["relative_path"]
        ).replace("/", "\\")

        mapping[relative_path.lower()] = (
            row["capture_session"]
        )

    return mapping


# ============================================================
# PROCESS CHUNK
# ============================================================

def process_chunk(df, capture_session):

    # --------------------------------------------------------
    # Remove unwanted columns
    # --------------------------------------------------------

    existing_drop = [
        col for col in DROP_COLUMNS
        if col in df.columns
    ]

    df = df.drop(
        columns=existing_drop,
        errors="ignore"
    )

    # --------------------------------------------------------
    # SIP
    # --------------------------------------------------------

    if "SIP" in df.columns:

        sip_features = extract_ip_features(
            df["SIP"],
            "SIP"
        )

        df = pd.concat(
            [
                df.drop(columns=["SIP"]),
                sip_features
            ],
            axis=1
        )

    # --------------------------------------------------------
    # DIP
    # --------------------------------------------------------

    if "DIP" in df.columns:

        dip_features = extract_ip_features(
            df["DIP"],
            "DIP"
        )

        df = pd.concat(
            [
                df.drop(columns=["DIP"]),
                dip_features
            ],
            axis=1
        )

    # --------------------------------------------------------
    # HTTP METHOD
    # --------------------------------------------------------

    if "HTTPRM_M" in df.columns:

        df["HTTPRM_M"] = (
            df["HTTPRM_M"]
            .map(HTTP_MAPPING)
            .fillna(-1)
            .astype("int8")
        )

    # --------------------------------------------------------
    # RTSP METHOD
    # --------------------------------------------------------

    if "RTSP_MM" in df.columns:

        df["RTSP_MM"] = (
            df["RTSP_MM"]
            .map(RTSP_MAPPING)
            .fillna(-1)
            .astype("int8")
        )

    # --------------------------------------------------------
    # Target cleanup
    # --------------------------------------------------------

    if TARGET in df.columns:

        df[TARGET] = (
            df[TARGET]
            .astype(str)
            .str.strip()
        )

    # --------------------------------------------------------
    # Add capture session metadata
    # --------------------------------------------------------

    df["capture_session"] = capture_session

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("MU-IoT FULL PREPROCESSING")
    print("=" * 80)

    print("\nLoading capture-session mapping...")

    session_mapping = load_session_mapping()

    print(
        f"Session mappings loaded: "
        f"{len(session_mapping)}"
    )

    csv_files = sorted(
        ROOT.rglob("*.csv")
    )

    print(
        f"CSV files found: {len(csv_files)}"
    )

    if len(csv_files) != 40:

        raise RuntimeError(
            f"Expected 40 CSV files, "
            f"found {len(csv_files)}"
        )

    # --------------------------------------------------------
    # Remove previous output if it exists
    # --------------------------------------------------------

    if OUTPUT_FILE.exists():

        print(
            "\nExisting output found."
        )

        print(
            f"Deleting: {OUTPUT_FILE}"
        )

        OUTPUT_FILE.unlink()

    first_write = True

    total_rows = 0

    global_class_counts = {}

    # --------------------------------------------------------
    # Process every CSV
    # --------------------------------------------------------

    for file_number, file_path in enumerate(
        csv_files,
        start=1
    ):

        relative_path = str(
            file_path.relative_to(ROOT)
        ).replace("/", "\\")

        lookup_key = relative_path.lower()

        if lookup_key not in session_mapping:

            raise RuntimeError(
                "No capture-session mapping found for:\n"
                f"{relative_path}"
            )

        capture_session = session_mapping[
            lookup_key
        ]

        print("\n" + "-" * 80)

        print(
            f"[{file_number}/{len(csv_files)}] "
            f"{relative_path}"
        )

        print(
            f"Session: {capture_session}"
        )

        file_rows = 0

        # ----------------------------------------------------
        # Read in chunks
        # ----------------------------------------------------

        for chunk_number, chunk in enumerate(
            pd.read_csv(
                file_path,
                chunksize=CHUNK_SIZE,
                low_memory=False
            ),
            start=1
        ):

            processed = process_chunk(
                chunk,
                capture_session
            )

            rows = len(processed)

            file_rows += rows
            total_rows += rows

            # ------------------------------------------------
            # Class distribution
            # ------------------------------------------------

            if TARGET in processed.columns:

                counts = (
                    processed[TARGET]
                    .value_counts()
                )

                for category, count in counts.items():

                    global_class_counts[
                        category
                    ] = (
                        global_class_counts.get(
                            category,
                            0
                        )
                        + int(count)
                    )

            # ------------------------------------------------
            # Save chunk
            # ------------------------------------------------

            processed.to_csv(
                OUTPUT_FILE,
                mode="w" if first_write else "a",
                header=first_write,
                index=False
            )

            first_write = False

            print(
                f"  Chunk {chunk_number}: "
                f"{rows:,} rows"
            )

            del chunk
            del processed

        print(
            f"File total: {file_rows:,} rows"
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 80)
    print("FULL PREPROCESSING COMPLETE")
    print("=" * 80)

    print(
        f"\nTotal processed rows: "
        f"{total_rows:,}"
    )

    print(
        f"Output file:\n"
        f"{OUTPUT_FILE}"
    )

    print("\nClass distribution:")

    for category, count in sorted(
        global_class_counts.items(),
        key=lambda x: x[1],
        reverse=True
    ):

        print(
            f"  {category:20} "
            f"{count:,}"
        )

    print("\nDONE.")


if __name__ == "__main__":
    main()