#! /usr/bin/env python3

from pathlib import Path
import time

from octopost import __version__
print(f"Octopost version: {__version__}")

from octopost.postproc import forces,residuals,actuatorDisk

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

    if False:    
        r = residuals(case_dir=case_dir)
        print(r)
        
        ad = actuatorDisk(case_dir=case_dir, base_dir='actuatorDisk1')
        print(ad)
    
    
if __name__ == "__main__":
    main()