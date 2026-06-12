#!/usr/bin/env python3

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from octopost.parsing import list_time_dirs,parse_of

def makeRuntimeSelectableReader(reader_name,base_dir,case_dir=None):
    """
    Factory function to create OpenFOAM postprocessing readers.
    
    Parameters
    ----------
    reader_name : str
        Name of the reader class to instantiate. Must be one of the
        OpenFOAM postprocessing reader classes defined in this module,
        e.g. 'OpenFOAMforces', 'OpenFOAMresiduals', etc
    base_dir : str or Path
        Base directory inside the OpenFOAM case 'postProcessing' folder
    case_dir : str or Path, optional
        Path to the OpenFOAM case directory. If None, the current working
        directory is used. Default is None.
        
    Returns
    -------
    reader : OpenFOAMpostProcessing
        An instance of the requested OpenFOAM postprocessing reader class.
    """
            
    if case_dir is None:
        case_dir = Path.cwd()
    
    reader_name = "OpenFOAM{0:}".format(reader_name)
    
    if reader_name == "OpenFOAMrigidBodyState":
        reader = getattr(sys.modules[__name__],reader_name)(file_name=base_dir,case_dir=case_dir)
    else:
        reader = getattr(sys.modules[__name__],reader_name)(base_dir=base_dir,case_dir=case_dir)
    
    return reader

class OpenFOAMpostProcessing(object):
    """
    Base class for OpenFOAM postprocessing data readers.
    """
    SORT_ORDER = {'time':-1}
    stats = None
    
    def combine_oftime_files(self,file_name,names,usecols):      

        time_dirs = list_time_dirs(self.base_dir)
            
        if not time_dirs:
            self.data = pd.DataFrame()
            return
        
        current_mtime = np.amax([Path(td,file_name).stat().st_mtime for td in time_dirs])
        
        verbose = True
        if current_mtime == self.mtime: # no need to reload
            if verbose: print('no need to reload, we are up to date')
            self.up_to_date = True
        else:
            self.up_to_date = False
            self.mtime = current_mtime
            
            tmp_data = []
        
            for td in time_dirs:
                p = Path(td,file_name)
                df = parse_of(p,names,usecols)
                try:
                    tmp_data.append(df.set_index('time'))
                except KeyError as e:
                    tmp_data.append(df.set_index(0))
        
            d = tmp_data[-1]
               
            if len(tmp_data) > 1:
                for i in reversed(tmp_data[:-1]):
                    if i.index.array[-1] > d.index.array[-1]: 
                        i = i[i.index < d.index.array[-1]]
                    d = d.combine_first(i)
            
            # combine_first() can leave a highly fragmented frame; copy()
            # defragments before adding the index back as a column.
            self.data = d.copy()
            self.data.reset_index(inplace=True)


    def sort_fields(self):
          
        try: 
            self.data = self.data.reindex(sorted(self.data.columns,key=lambda val: self.SORT_ORDER[val]),axis=1)
        except KeyError as e:
            pass 
            #print(e)

    def fields(self):
        
        f = list(self.data.columns)
        f.remove('time')
        
        return f
    
    def __str__(self):
        
        return str(self.data.head())
    
    def __init__(self,base_dir,file_name,names=None,usecols=None,case_dir=None,tmin=None,tmax=None):
        """
        Parameters
        ----------
        base_dir : str or Path
            Base directory inside the OpenFOAM case 'postProcessing' folder
        file_name : str
            Name of the file inside each time directory to read, e.g. 'forces.dat'
        names : list of str, optional
            List of column names to use when reading the data file. If None,
            default names are used. Default is None.
        usecols : list of str, optional
            List of column names to read from the data file. If None, all columns
            are read. Default is None.
        case_dir : str or Path, optional
            Path to the OpenFOAM case directory. If None, the current working
            directory is used. Default is None.
        tmin : float, optional
            Minimum time value to filter the data. If None, no minimum time
            filtering is applied. Default is None.
        tmax : float, optional
            Maximum time value to filter the data. If None, no maximum time
            filtering is applied. Default is None.
        """
        
        self.mtime = 0
        self.up_to_date = False
        
        # create and empty reader  # not sure if this makes sense
        if base_dir is None and file_name is None:
            self.data = pd.DataFrame() #columns={'time':[]})
            return

        self.base_dir = base_dir

        self.file_name = file_name
       
        self.case_dir = case_dir
       
        if case_dir is None:
            self.case_dir = Path.cwd()
        
        self.tmin,self.tmax = tmin,tmax
                
        self.names = names
        
        self.usecols = usecols
        
        self.base_dir = Path(self.case_dir,'postProcessing',base_dir)
                   
        self.load_data()
        

    def load_data(self):
        
        self.combine_oftime_files(self.file_name, self.names, self.usecols)

        if not self.up_to_date:
            self.customize()
    
    def get_data(self):
        
        self.load_data()
        
        return self.data
    
    def customize(self):
        
        pass
        

    def time_range(self):

        if self.tmin is not None:
            self.data = self.data[self.data['time'] > self.tmin]
        
        if self.tmax is not None:
            self.data = self.data[self.data['time'] < self.tmax]

    def describe_stats(self, time_range=None):
        """
        Return summary stats for non-time columns.

        Parameters
        ----------
        time_range : None, scalar, tuple/list len 2, or list of len-2 tuples/lists
            None uses the full time range. A scalar is treated as the lower bound.
            A (start, end) pair selects a bounded range; use None for open ends.
            A list of ranges computes stats for each range.

        Returns
        -------
        pandas.DataFrame or list of dict
            Summary stats (count, min, max, mean). For multiple ranges, a list of
            dicts with keys 'time_range' and 'stats' is returned.
        """

        df = self.get_data()

        def normalize_ranges(value):
            if value is None:
                return [(None, None)]
            if isinstance(value, (int, float, np.number)):
                return [(value, None)]
            if isinstance(value, (list, tuple)):
                if len(value) == 2 and not (
                    isinstance(value[0], (list, tuple)) or isinstance(value[1], (list, tuple))
                ):
                    return [tuple(value)]
                if len(value) > 0 and all(
                    isinstance(item, (list, tuple)) and len(item) == 2 for item in value
                ):
                    return [tuple(item) for item in value]
            raise ValueError("time_range must be None, scalar, len-2 range, or list of ranges")

        ranges = normalize_ranges(time_range)
        results = []

        print(ranges)

        for start, end in ranges:
            subset = df
            if start is not None:
                subset = subset.loc[subset['time'] >= start]
            if end is not None:
                subset = subset.loc[subset['time'] <= end]

            data = subset.drop(columns=['time'], errors='ignore')
            stats = data.agg(['count', 'min', 'max', 'mean'])
            stats = stats.reindex(['count', 'min', 'max', 'mean'])
            results.append({'time_range': (start, end), 'stats': stats})

        if len(results) == 1:
            self.stats = results[0]['stats']
            return self.stats

        self.stats = results
        return self.stats


class OpenFOAMforces(OpenFOAMpostProcessing):
    
    def __init__(self,base_dir='forces',file_name='forces.dat',case_dir=None,tmin=None,tmax=None):

        self.SORT_ORDER = {'time':-1, "fx": 0}
        
        super().__init__(base_dir=base_dir,file_name=file_name,case_dir=case_dir,names=None,usecols=None,tmin=tmin,tmax=tmax)
        
    def customize(self):
        OpenFOAMpostProcessing.customize(self)

        if not self.data.empty and self.usecols is None:

            self.data.dropna(how='all',axis=1,inplace=True)            

            if len(self.data.columns == 13):
                self.names = ['time','fxp','fyp','fzp','fxv','fyv','fzv','mxp','myp','mzp','mxv','myv','mzv']        
            else:
                self.names = ['time','fxp','fyp','fzp','fxv','fyv','fzv','fxpor','fypor','fzpor', 'mxp','myp','mzp','mxv','myv','mzv','mxpor','mypor','mzpor']

            self.usecols = ['time','fxp','fyp','fzp','fxv','fyv','fzv','mxp','myp','mzp','mxv','myv','mzv']

            for i in range(1,len(self.usecols)):
                self.SORT_ORDER[self.usecols[i]] = i
            
            mapper = dict(zip(self.data.columns,self.usecols))
            
            self.data.rename(columns=mapper,inplace=True)        
        
        try:
            self.data['fx'] = self.data['fxp'] + self.data['fxv']
        except KeyError:
            pass
        
        self.time_range()
        
        self.sort_fields()


class OpenFOAMwaveBuoy(OpenFOAMpostProcessing):
    
    def __init__(self,base_dir='waveBuoy',file_name='height.dat',case_dir=None,tmin=None,tmax=None):
        self.locations = []
        super().__init__(base_dir=base_dir, file_name=file_name, names=None, usecols=None, case_dir=case_dir, tmin=tmin, tmax=tmax)

    def _read_locations_from_header(self):
        loc_pattern = re.compile(r"^\s*#\s*Location\s+(\d+)\s*:\s*(.*)\s*$")
        time_dirs = list_time_dirs(Path(self.base_dir))

        for td in time_dirs:
            p = Path(td, self.file_name)
            if not p.exists():
                continue

            loc_values = {}
            with p.open('r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if not line.lstrip().startswith('#'):
                        break

                    m = loc_pattern.match(line)
                    if m:
                        idx = int(m.group(1))
                        raw = m.group(2).replace('(', ' ').replace(')', ' ').strip()
                        parts = raw.split()
                        try:
                            values = tuple(float(x) for x in parts)
                        except ValueError:
                            values = tuple(parts)
                        loc_values[idx] = values

            if loc_values:
                n_locs = max(loc_values.keys()) + 1
                locations = [np.nan] * n_locs
                for idx, value in loc_values.items():
                    locations[idx] = value
                return locations

        return []

    def customize(self):
        OpenFOAMpostProcessing.customize(self)
        
        if self.data.empty:
            self.locations = []
            return

        self.locations = self._read_locations_from_header()
        self.data.dropna(how='all',axis=1,inplace=True)
        
        # get only the height above the location, i. e. every second entry
        cols = ['time'] + list(self.data)[2::2]
        self.data = self.data.loc[:,cols]
        
        mapDict = {key:f'buoy{i}' for i,key in enumerate(list(self.data)[1:]) }
        self.data.rename(columns=mapDict,inplace=True)

        n_buoys = len(self.data.columns) - 1
        if not self.locations:
            self.locations = [np.nan] * n_buoys
        elif len(self.locations) < n_buoys:
            self.locations.extend([np.nan] * (n_buoys - len(self.locations)))
        elif len(self.locations) > n_buoys:
            self.locations = self.locations[:n_buoys]

        self.data.attrs['locations'] = self.locations
        
        
        self.time_range()    
        
        


class OpenFOAMrigidBodyState(OpenFOAMpostProcessing):
    
    def __init__(self,base_dir='rigidBodyState',file_name='hull.dat',case_dir=None,subtractInitialCoG=True,tmin=None,tmax=None):
        
        self.subtractInitialCoG = subtractInitialCoG

        names = ['time','x','y','z','roll','pitch','yaw','vx','vy','vz','vroll','vpitch','vyaw']
        
        super().__init__(base_dir=base_dir,file_name=file_name,names=names,usecols=None,case_dir=case_dir,tmin=tmin,tmax=tmax)
        
        
    def customize(self):
        OpenFOAMpostProcessing.customize(self)
        
        if self.data.size != 0:
            if self.subtractInitialCoG:
                for dof in ['x','y','z']:
                    self.data[dof] = self.data[dof] - self.data[dof].iloc[0]
        
        self.time_range()

class OpenFOAMresiduals(OpenFOAMpostProcessing):
    
    def __init__(self,base_dir='residuals',file_name='residuals.dat',case_dir=None,tmin=None,tmax=None):
        
        self.SORT_ORDER = {"U": 0, "Ux": 1, "Uy": 2, "Uz": 3, "p": 4, "p_rgh": 5, "k": 6, "omega":7,'time':-1}
        
        super().__init__(base_dir=base_dir,file_name=file_name,names=None,usecols=None,case_dir=case_dir,tmin=tmin,tmax=tmax)
        
    
    def customize(self): 
        OpenFOAMpostProcessing.customize(self)

        if not self.data.empty and self.usecols is None:
        
            self.data.dropna(how='all',axis=1,inplace=True)
            
            time_dirs = list_time_dirs(Path(self.base_dir))
                        
            with Path(self.base_dir,time_dirs[0],'residuals.dat').open('r') as f:
                for i,line in enumerate(f):
                    if i == 1:
                        header = line
                        break
    
            header = header.replace('#','').split()[:]
            header[0] = 'time'
    
            self.names = header
            self.usecols = header
            
            mapper = dict(zip(self.data.columns,self.usecols))
            
            self.data.rename(columns=mapper,inplace=True)

        try:
            self.data['U'] = (np.abs(self.data['Ux'].pow(2) + self.data['Uy'].pow(2) + self.data['Uz'].pow(2)))/3.
            self.data.drop(columns=['Ux','Uy','Uz'],inplace=True)    
        except KeyError:
            pass

        self.time_range()
            
        self.sort_fields()
        

class OpenFOAMtime(OpenFOAMpostProcessing):
    
    def __init__(self,base_dir,file_name='time.dat',case_dir=None,tmin=None,tmax=None):
        
        super().__init__(base_dir=base_dir,file_name=file_name,names=None,usecols=None,case_dir=case_dir,tmin=tmin,tmax=tmax)
        
        
    def customize(self):
        OpenFOAMpostProcessing.customize(self)
                
        if not self.data.empty and self.usecols is None:
            self.data.dropna(how='all',axis=1,inplace=True)
            
            time_dirs = list_time_dirs(Path(self.base_dir))
            
            with Path(self.base_dir,time_dirs[0],'time.dat').open('r') as f:
                for i,line in enumerate(f):
                    if i == 1:
                        header = line
                        break
                    
            header = header.replace('#','').split()[:]
            header[0] = 'time'
    
            self.names = header
            self.usecols = header
            
            mapper = dict(zip(self.data.columns,self.usecols))
            
            self.data.rename(columns=mapper,inplace=True)
                
        self.time_range()
        
        
class OpenFOAMfieldMinMax(OpenFOAMpostProcessing):
    
    def __init__(self,base_dir,file_name='fieldMinMax.dat',case_dir=None,tmin=None,tmax=None):
        
        names = ['time','field','min','locationX(min)','locationY(min)','locationZ(min)','processor(min)','max','locationX(max)','locationY(max)','locationZ(max)','processor(max)']
        usecols = ['time','field','min','max']
        
        super().__init__(base_dir=base_dir,file_name=file_name,names=names,usecols=usecols,case_dir=case_dir,tmin=tmin,tmax=tmax)
        
        
    def customize(self):
        OpenFOAMpostProcessing.customize(self)
        
        fields = self.data['field'].unique()
    
        dfs = [self.data.loc[self.data['field'] == field] for field in fields ]
        dfs = [df.drop(columns=['field']) for df in dfs]
        dfs = [df.set_index('time',drop=True) for df in dfs]
        
        for i,df in enumerate(dfs):
            mapper = {k:"{0:}_{1:}".format(k,fields[i]) for k in list(df.columns)}
            df.rename(columns=mapper,inplace=True)
        
        self.data = pd.concat(dfs,axis=1)
        
        self.data['time'] = self.data.index
        
        self.time_range()
    
class OpenFOAMvp(OpenFOAMpostProcessing):
    
    def __init__(self,base_dir='vp',file_name='volFieldValue.dat',case_dir=None):
        
        names = ['time','vpx','vpy','vpz']
        usecols = ['time','vpx']
        
        super().__init__(base_dir=base_dir, file_name=file_name, names=names, usecols=usecols, case_dir=case_dir)
        
class OpenFOAMactuatorDisk(OpenFOAMpostProcessing):

    SCHEMAS = {
        12: ['time','thrust','duct_thrust','torque','vp','va','n','J','FD','alphacorrThrust','alphacorrTorque','fillgrade'],
        11: ['time','thrust','torque','vp','va','n','J','FD','alphacorrThrust','alphacorrTorque','fillgrade'],
        7: ['time','thrust','torque','vp','va','n','FD'],
    }
    
    def __init__(self,base_dir='actuatorDisk',file_name='actuatorDisk.dat',case_dir=None,tmin=None,tmax=None):

        if case_dir is None:
            case_dir = Path.cwd()

        post_dir = Path(case_dir,'postProcessing',base_dir)
        n_cols = self._read_column_count(post_dir, file_name)
        try:
            names = self.SCHEMAS[n_cols]
        except KeyError:
            supported = ', '.join(str(k) for k in sorted(self.SCHEMAS))
            raise ValueError(
                f"Unsupported actuatorDisk column count ({n_cols}) in {file_name}. "
                f"Expected one of: {supported}."
            )

        super().__init__(
            base_dir=base_dir,
            file_name=file_name,
            names=names,
            usecols=names,
            case_dir=case_dir,
            tmin=tmin,
            tmax=tmax,
        )

    @staticmethod
    def _read_column_count(base_dir, file_name):
        for td in list_time_dirs(base_dir):
            p = Path(td,file_name)
            if not p.exists():
                continue

            trantab = str.maketrans('()','  ')
            with p.open('r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.lstrip().startswith('#') or not line.strip():
                        continue
                    return len(line.translate(trantab).split())

        raise ValueError(f"No numeric data found in actuatorDisk file: {Path(base_dir,file_name)}")

    def customize(self):
        OpenFOAMpostProcessing.customize(self)
        self.time_range()


class OpenFOAMsectionalForces(OpenFOAMpostProcessing):

    def __init__(
        self,
        base_dir='sectionalLoads',
        file_name='rigidBodySectionalForceProbes.dat',
        case_dir=None,
        tmin=None,
        tmax=None,
        sep=' ',
        quantity='total',
    ):
        self.sep = sep
        self.quantity = quantity
        self.coordinates = []
        self.SORT_ORDER = {'time': -1}
        super().__init__(
            base_dir=base_dir,
            file_name=file_name,
            names=None,
            usecols=None,
            case_dir=case_dir,
            tmin=tmin,
            tmax=tmax,
        )

    @staticmethod
    def _parse_coordinate_value(raw_value):
        cleaned = raw_value.replace('(', ' ').replace(')', ' ').strip()
        if not cleaned:
            return np.nan

        parts = cleaned.split()
        try:
            nums = [float(p) for p in parts]
        except ValueError:
            return cleaned

        if len(nums) == 1:
            return nums[0]
        return tuple(nums)

    def _read_coordinates_from_header(self):
        coord_pattern = re.compile(r"^\s*#\s*Coordinate\s+(\d+)\s*:\s*(.*)\s*$")
        time_dirs = list_time_dirs(Path(self.base_dir))

        for td in time_dirs:
            p = Path(td, self.file_name)
            if not p.exists():
                continue

            coord_values = {}
            with p.open('r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.lstrip().startswith('#'):
                        m = coord_pattern.match(line)
                        if m:
                            idx = int(m.group(1))
                            coord_values[idx] = self._parse_coordinate_value(m.group(2))
                    else:
                        break

            if coord_values:
                n_coords = max(coord_values.keys()) + 1
                coordinates = [np.nan] * n_coords
                for idx, value in coord_values.items():
                    coordinates[idx] = value
                return n_coords, coordinates

        return None, []

    def _build_column_names(self, n_coords, quantities=None):
        components = ['x', 'y', 'z']
        all_quantities = [
            'Fluid Force',
            'Body Force',
            'Total Force',
            'Fluid Moment',
            'Body Moment',
            'Total Moment',
        ]
        if quantities is None:
            quantities = all_quantities

        names = ['time']
        for s in range(n_coords):
            for quantity in quantities:
                for component in components:
                    names.append(f"S{s}{self.sep}{quantity}{self.sep}{component}")

        return names

    def _selected_quantities(self):
        selection = str(self.quantity).strip().lower()
        mapper = {
            'fluid': ['Fluid Force', 'Fluid Moment'],
            'body': ['Body Force', 'Body Moment'],
            'total': ['Total Force', 'Total Moment'],
            'all': [
                'Fluid Force',
                'Body Force',
                'Total Force',
                'Fluid Moment',
                'Body Moment',
                'Total Moment',
            ],
        }
        if selection not in mapper:
            raise ValueError(
                f"Unsupported quantity selection: {self.quantity}. "
                "Use one of: 'fluid', 'body', 'total', 'all'."
            )
        return mapper[selection]

    def customize(self):
        OpenFOAMpostProcessing.customize(self)

        if not self.data.empty and self.usecols is None:
            self.data.dropna(how='all', axis=1, inplace=True)

            n_cols = self.data.shape[1]
            if n_cols < 2:
                raise ValueError(
                    f"Unexpected column count ({n_cols}) in file: {self.file_name}"
                )

            n_after_time = n_cols - 1
            per_coord = 18  # 6 vectors * 3 components

            n_coords, coordinates = self._read_coordinates_from_header()
            self.coordinates = coordinates
            if n_coords is None:
                if n_after_time % per_coord != 0:
                    raise ValueError(
                        "Cannot infer number of coordinates: "
                        f"columns after time = {n_after_time} is not divisible by {per_coord}."
                    )
                n_coords = n_after_time // per_coord
                if not self.coordinates:
                    self.coordinates = [np.nan] * n_coords
            else:
                expected = n_coords * per_coord
                if n_after_time != expected:
                    raise ValueError(
                        f"Header indicates {n_coords} coordinates -> expected {1 + expected} "
                        f"columns, but found {n_cols}."
                    )

            full_columns = self._build_column_names(n_coords)

            if len(full_columns) != n_cols:
                raise RuntimeError(
                    f"Internal mismatch: built {len(full_columns)} column names, "
                    f"file has {n_cols} columns."
                )

            mapper = dict(zip(self.data.columns, full_columns))
            self.data.rename(columns=mapper, inplace=True)

            selected_quantities = self._selected_quantities()
            selected_columns = self._build_column_names(n_coords, quantities=selected_quantities)
            self.usecols = selected_columns

            self.data = self.data.loc[:, selected_columns]

            self.SORT_ORDER = {'time': -1}
            for i, col in enumerate(selected_columns[1:], start=0):
                self.SORT_ORDER[col] = i

        self.data.attrs['coordinates'] = self.coordinates
        self.time_range()
        self.sort_fields()


def residuals(base_dir='residuals',case_dir=None):
    return OpenFOAMresiduals(base_dir=base_dir,case_dir=case_dir).data

def forces(base_dir='forces',file_name='forces.dat',case_dir=None,tmin=None,tmax=None):
    return OpenFOAMforces(base_dir=base_dir,file_name=file_name,case_dir=case_dir,tmin=tmin,tmax=tmax).data
    
def rigidBodyState(file_name='hull.dat',case_dir=None,tmin=None,tmax=None):
    return OpenFOAMrigidBodyState(file_name=file_name,case_dir=case_dir,tmin=tmin,tmax=tmax).data

def time(base_dir='timeMonitor',case_dir=None,drop_columns=['cpu','clock']):
    return OpenFOAMtime(base_dir=base_dir,case_dir=case_dir).data.drop(columns=drop_columns)

def actuatorDisk(base_dir='actuatorDisk',file_name='actuatorDisk.dat',case_dir=None,tmin=None,tmax=None):
    return OpenFOAMactuatorDisk(base_dir=base_dir,file_name=file_name,case_dir=case_dir,tmin=tmin,tmax=tmax).data

def waveBuoy(base_dir='waveBuoy',file_name='height.dat',case_dir=None,tmin=None,tmax=None):
    return OpenFOAMwaveBuoy(base_dir=base_dir,file_name=file_name,case_dir=case_dir,tmin=tmin,tmax=tmax).data

def sectionalForces(base_dir='sectionalLoads',file_name='rigidBodySectionalForceProbes.dat',case_dir=None,tmin=None,tmax=None,sep=' ',quantity='total'):
    return OpenFOAMsectionalForces(base_dir=base_dir,file_name=file_name,case_dir=case_dir,tmin=tmin,tmax=tmax,sep=sep,quantity=quantity).data

def main():

    #r = OpenFOAMforces() 
    #r = OpenFOAMresiduals()
    #r = OpenFOAMtime(base_dir='timeMonitor')
    r = OpenFOAMfieldMinMax(base_dir='minMaxMag')
    print(r.data)
    r.load_data()
    print(r.data)

    if False:    
        t = OpenFOAMtime(base_dir='timeMonitor')
        
        t = OpenFOAMfieldMinMax(base_dir='minMaxMag')
        fields = t.data.field.unique()
        
        dfs = [t.data.loc[t.data['field'] == field] for field in fields ]
        dfs = [df.drop(columns=['field']) for df in dfs]
        dfs = [df.set_index('time',drop=True) for df in dfs]
        for i,df in enumerate(dfs):
            mapper = {k:"{0:}_{1:}".format(k,fields[i]) for k in list(df.columns)}
            df.rename(columns=mapper,inplace=True)
            
        result = pd.concat(dfs,axis=1)
        print(result)
 


if __name__ == '__main__':
    main()
