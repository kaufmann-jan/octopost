# octopost

## Module docs
See [src/octopost/README.md](src/octopost/README.md) for the in-package README used by the module.

```bash
pip install octopost@git+https://github.com/kaufmann-jan/octopost
```

```python
from octopost.reader import forces

df = forces(case_dir="/path/to/case")
```

```python
from octopost.reader import OpenFOAMresiduals

res = OpenFOAMresiduals(case_dir="/path/to/case", tmin=0.5, tmax=10.0)
df = res.get_data()
```
