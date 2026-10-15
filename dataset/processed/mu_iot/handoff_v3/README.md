# MU-IoT Handoff V3

Generated from the canonical cleaned master:

`D:\Major_Project\dataset\processed\mu_iot\mu_iot_cleaned.csv`

## Feature set

Existing feature key:

`paper_top48_coverage95_nonconstant`

Existing feature count:

40

Removed:

- FPT
- LPT

Final feature key:

`paper_top48_coverage95_nonconstant_38`

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

10,000

Minimum block size:

20

No partial block is allowed.

## Caps

Train:

500,000

Validation:

100,000

Within-session test:

150,000

Each held-out session:

200,000

## Scaling

`StandardScaler` is fitted only on selected TRAIN rows.

Train rows used for scaler fitting:

2,171,995

## Output

Full rows:

3,936,753

Pilot rows:

154,608

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
