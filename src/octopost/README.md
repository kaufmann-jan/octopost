# octopost module

Small OpenFOAM post-processing helpers that load `postProcessing/<base_dir>/<time>/`
files into pandas DataFrames.

## What it provides
- Reader classes for common OpenFOAM outputs (forces, residuals, rigid body state, time monitor, field min/max, etc.).
- Convenience functions that return `pandas.DataFrame` directly.
- Optional time filtering via `tmin`/`tmax`.

## Requirements
- Python 3.7+
- numpy
- pandas

## Install (from repo)
```bash
pip install octopost@git+https://github.com/kaufmann-jan/octopost
```

## Quick start
```python
from octopost.reader import OpenFOAMforces, forces

# Explicit reader instance (reloads on demand)
reader = OpenFOAMforces(case_dir="/path/to/case")
df = reader.get_data()

# Convenience function
df = forces(case_dir="/path/to/case")
```

## Reader overview
```python
from octopost.reader import (
    OpenFOAMforces,
    OpenFOAMresiduals,
    OpenFOAMrigidBodyState,
    OpenFOAMtime,
    OpenFOAMfieldMinMax,
    OpenFOAMwaveBuoy,
    OpenFOAMactuatorDisk,
)
```

All readers look under `postProcessing/<base_dir>/` inside `case_dir` and
combine data across time directories. Each reader customizes columns and
sorting; use `reader.fields()` to list non-time columns.

## Using tmin/tmax
```python
from octopost.reader import OpenFOAMresiduals

res = OpenFOAMresiduals(case_dir="/path/to/case", tmin=0.5, tmax=10.0)
df = res.get_data()
```

## Convenience functions
```python
from octopost.reader import (
    residuals,
    forces,
    rigidBodyState,
    time,
    actuatorDisk,
    waveBuoy,
)
```

## File layout
- `src/octopost/reader.py` defines readers and convenience functions.
- `src/octopost/parsing.py` contains parsing helpers.

## Notes
- The readers auto-combine time directories; reloads are skipped if files are unchanged.
- `case_dir` defaults to the current working directory when not provided.

## License
GPLv3 (see `LICENSE.md` at repo root).

## Contributing
Contributions are welcome. Please open an issue or pull request in the main
repository with a clear description of the change and any relevant tests or
data notes.

## Changelog
Track notable changes in the main repository's release notes or tags.
