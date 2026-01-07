#! /usr/bin/env python3

from pathlib import Path
import time

from octopost import __version__
print(f"Octopost version: {__version__}")

from octopost.reader import OpenFOAMforces
from octopost.reader import forces,residuals,actuatorDisk,rigidBodyState
from octopost.reader import time as pp_time

def main():
    
    print("Testing octopost postprocessing module...")
    
    data_dir = Path(__file__).parent / ".." / "data"
    
    if not data_dir.exists():
        print(f"Data directory does not exist: {data_dir}")
        
    case_dir = data_dir / "case3"
    
    t0 = time.perf_counter()
    f = forces(case_dir=case_dir)
    elapsed = time.perf_counter() - t0
    print(f"forces() execution time: {elapsed:.6f} s")
    print(f)
        
    r = residuals(case_dir=case_dir)
    print(r)
        
    ad = actuatorDisk(case_dir=case_dir, base_dir='actuatorDisk1')
    print(ad)
    
    rbs = rigidBodyState(case_dir=case_dir, file_name='hull.dat')
    print(rbs)
    
    t = pp_time(case_dir=case_dir)
    print(t)
    
    f = OpenFOAMforces(case_dir=case_dir, file_name='forces.dat')
    #print(f.data)
    print(f.describe_stats())
    print(f.describe_stats(time_range=[(500,None),(None,100)]))
    
    
if __name__ == "__main__":
    main()
