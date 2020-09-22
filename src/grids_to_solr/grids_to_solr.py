import os
import sys
import json
import yaml
import requests
import xarray as xr
from datetime import datetime
from urllib.request import urlopen, urlcleanup, urlretrieve

def main(path=''):
    # =====================================================
    # Read configurations from YAML file
    # =====================================================
    if path:
        path_to_yaml = f'{path}/grids_config.yaml'
        path_to_file_dir = f'{path}/grids/'
    else:
        path_to_yaml = f'{os.path.dirname(sys.argv[0])}/grids_config.yaml'
        path_to_file_dir = f'{os.path.dirname(sys.argv[0])}/grids/'
    with open(path_to_yaml, "r") as stream:
        config = yaml.load(stream, yaml.Loader)

    solr_host = config['solr_host']
    solr_collection_name = config['solr_collection_name']

    # =====================================================
    # Scan directory for grid types
    # =====================================================
    grid_files = [f for f in os.listdir(path_to_file_dir) if os.path.isfile(
        os.path.join(path_to_file_dir, f))]

    # =====================================================
    # Extract grid names from netCDF
    # =====================================================
    grids = []

    # Assumes grids conform to metadata standard (model_grid_type)
    for grid_file in grid_files:
        if config['grids_to_use']:
            if grid_file in config['grids_to_use']:
                ds = xr.open_dataset(path_to_file_dir + grid_file)

                grid_name = ds.attrs['name']
                grid_type = ds.attrs['type']
                grids.append((grid_name, grid_type, grid_file))
        else:
            ds = xr.open_dataset(path_to_file_dir + grid_file)

            grid_name = ds.attrs['name']
            grid_type = ds.attrs['type']
            grids.append((grid_name, grid_type, grid_file))


    # =====================================================
    # Query for Solr Grid-type Documents
    # =====================================================

    getVars = {'q': '*:*',
               'fq': ['type_s:grid'],
               'rows': 300000}

    url = solr_host + solr_collection_name + '/select?'
    response = requests.get(url, params=getVars)
    docs = response.json()['response']['docs']

    grids_in_solr = []
    grid_metas = []

    if len(docs) > 0:
        for doc in docs:
            grids_in_solr.append(doc['grid_name_s'])

    # =====================================================
    # Create Solr grid-type document for each missing grid type
    # =====================================================
    for grid_name, grid_type, grid_file in grids:
        if grid_name not in grids_in_solr:
            grid_meta = {}
            grid_meta['type_s'] = 'grid'
            grid_meta['grid_type_s'] = grid_type
            grid_meta['grid_name_s'] = grid_name
            grid_meta['grid_path_s'] = path_to_file_dir + grid_file
            grid_meta['date_added_dt'] = datetime.utcnow().strftime(
                "%Y-%m-%dT%H:%M:%SZ")
            grid_metas.append(grid_meta)

    url = solr_host + solr_collection_name + '/update?commit=true'

    r = requests.post(url, json=grid_metas)

    if r.status_code == 200:
        print('Successfully updated Solr grid document')
    else:
        print('Failed to update Solr grid document')


if __name__ == '__main__':
    main()