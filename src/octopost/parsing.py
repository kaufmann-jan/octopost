from io import StringIO
from pathlib import Path

import pandas as pd

def list_time_dirs(path_to_time_dirs):
    """Lists all time directories in a given path and returns them
    
    Parameters
    ----------
    path_to_time_dirs : str
        path to directory in which the time folders are stored. E.g. postProcessing/forces/ 
    
    Returns
    -------
    l : list of pathlib.Path
        list of paths to time directories sorted in ascending order
    """
    
    l = sorted([str(x.name) for x in Path(path_to_time_dirs).glob('[0-9]*')],key=float,reverse=False)
    l = [Path(path_to_time_dirs,p) for p in l]
    
    return l

def parse_of(file_name,names=None,usecols=None):
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
    df : pandas.DataFrame
        DataFrame containing the data from the text file
    
    """
    
    trantab = str.maketrans('()','  ')

    path = Path(file_name)

    with path.open('r') as f:
        fstream = StringIO(f.read().translate(trantab))
    
    df = pd.read_csv(
        fstream,
        sep=r"\s+",
        header=None,
        names=names,
        comment='#',
        usecols=usecols
    )

    return df

def dummy_columns(n=99):
    """Generates a list of dummy column names for OpenFOAM data files.
    
    Parameters
    ----------
    n : int, optional
        Number of dummy columns to generate (excluding the 'time' column). Default is 99.
        
    Returns
    -------
    names : list of str
        List of dummy column names, starting with 'time' followed by 'c0', '
        c1', ..., 'c{n-1}'.
    """
    
    names = ['time'] + ['c' + str(x) for x in range(n)]
    
    return names 

def filter_time_and_columns(df, time_start=None,time_end=None, data_subset=None):
    """Filtering time and sub-selecting data columns.
    
    Parameters
    ----------
    df : pandas.DataFrame
        The input data frame containing a 'time' column.
    time_start : float, optional
        The starting time to filter the data. Default is None, which means no lower limit.
    time_end : float, optional
        The ending time to filter the data. Default is None, which means no upper limit.
    data_subset : list, optional
        List of column names to select from the data frame. Default is None, which selects all
        columns.
        
    Returns
    -------
    pandas.DataFrame
        The prepared data frame with filtered time and selected columns.
    """
    
    if data_subset is None:
        data_subset = []

    if time_start is not None:
        df = df.loc[df.time >= time_start]
        
    if time_end is not None:
        df = df.loc[df.time <= time_end]

    df.set_index('time', drop=True, inplace=True)

    if len(data_subset) > 0:
        df = df[df.columns.intersection(data_subset)]

    return df