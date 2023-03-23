from io import StringIO
from pathlib import Path

import pandas as pd

def list_time_dirs(path_to_time_dirs):
    """
    
    Parameters
    ----------
    path_to_time_dirs : str
        path to directory in which the time folders are stored. E.g. postProcessing/forces/ 
    
    Returns
    -------
    
    list with time dir names as strings in sorted order
    
    """
    
    l = sorted([str(x.name) for x in Path(path_to_time_dirs).glob('[0-9]*')],key=float,reverse=False)
    l = [Path(path_to_time_dirs,p) for p in l]
    
    return l

def parse_of(file_name,names,usecols=None):
    """Opens a text file, replaces all brackets, i.e. () with 
    whitespaces, passes a file stream to the pandas csv read method
    and returns a pandas DataFrame.  
    
    Parameters
    ----------
    file_name : str
        name of the text file
    names : array-like, optional
        List of column names to use. For details see:
        https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
    usecols : list-like or callable, optional
        Return a subset of the columns. For details see: 
        https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
        
    Returns
    -------
    pandas DataFrame
    
    """
    
    trantab = str.maketrans('()','  ')

    path = Path(file_name)

    with path.open('r') as f:
        fstream = StringIO(f.read().translate(trantab))
    
    df = pd.read_csv(fstream,delim_whitespace=True,header=None,names=names,comment='#',usecols=usecols)

    return df


def dummy_columns(n=99):
    
    names = ['time'] + ['c' + str(x) for x in range(n)]
    
    return names 
