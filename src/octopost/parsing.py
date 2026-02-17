from pathlib import Path

import numpy as np
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
    """Parse OpenFOAM table-like output into a DataFrame.

    The parser is width-aware: it determines the maximum number of tokens per
    data line and pads shorter lines with NaN. This handles files where early
    lines have fewer fields (e.g. residuals at start-up) without requiring
    fixed dummy column counts.
    
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
    rows = []

    path = Path(file_name)

    with path.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.lstrip().startswith('#'):
                continue

            s = line.translate(trantab).strip()
            if not s:
                continue

            rows.append(s.split())

    if not rows:
        if names is not None:
            return pd.DataFrame(columns=names)
        return pd.DataFrame()

    max_cols = max(len(r) for r in rows)

    if names is None:
        col_names = ['time'] + [f'c{i}' for i in range(1, max_cols)]
    else:
        col_names = list(names)
        if len(col_names) < max_cols:
            col_names.extend([f'c_extra{i}' for i in range(max_cols - len(col_names))])

    n_cols = max(max_cols, len(col_names))
    padded_rows = [r + [np.nan] * (n_cols - len(r)) for r in rows]

    if len(col_names) < n_cols:
        col_names.extend([f'c_extra{i}' for i in range(n_cols - len(col_names))])

    df = pd.DataFrame(padded_rows, columns=col_names)
    df = df.apply(pd.to_numeric, errors='coerce')

    if usecols is not None:
        if callable(usecols):
            selected = [c for c in df.columns if usecols(c)]
            df = df.loc[:, selected]
        else:
            usecols_list = list(usecols)
            if usecols_list and all(isinstance(c, int) for c in usecols_list):
                df = df.iloc[:, usecols_list]
            else:
                df = df.loc[:, usecols_list]

    return df

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
