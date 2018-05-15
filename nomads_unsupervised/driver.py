from nomads import pipeline
from NeuroDataResource import NeuroDataResource
import pymeda_driver
import argparse
import pickle
import numpy as np
import boto3, glob
from nd_boss import boss_push
import csv

# pull data from BOSS
def get_data(host, token, col, exp, z_range, y_range, x_range):
    print("Downloading {} from {} with ranges: z: {} y: {} x: {}".format(exp, 
                                                                         col, 
                                                                         str(z_range), 
                                                                         str(y_range), 
                                                                         str(x_range)))
    resource = NeuroDataResource(host, token, col, exp)
    data_dict = {}
    for chan in resource.channels:
        data_dict[chan] = resource.get_cutout(chan, z_range, y_range, x_range)
    return data_dict, resource.voxel_size

# normalize data
def load_and_preproc(data_dict, z_transform=True):
    raw = data_dict
    if z_transform:
        for channel in raw.keys():
            #dont want to z transform annotations
            if channel != 'annotation':
                data = raw[channel]

                #get z transform stats
                for z_idx in range(data.shape[0]):
                    mu = np.mean(data[z_idx])
                    sigma = np.std(data[z_idx])
                    raw[channel][z_idx] = (raw[channel][z_idx] - mu)/sigma
    return raw
    
def format_data(data_dict):
    data = []
    for chan, value in data_dict.items():
        if "psd" in chan.lower() or "synapsin" in chan.lower():
            format_chan = []
            for z in range(value.shape[0]):
                raw = value[z]
                if (raw.dtype != np.dtype("uint8")):
                    info = np.iinfo(raw.dtype) # Get the information of the incoming image type
                    raw = raw.astype(np.float64) / info.max # normalize the data to 0 - 1
                    raw = 255 * raw # Now scale by 255
                    raw = raw.astype(np.uint8)
                #raw = pool(raw, (32, 32), np.mean)
                format_chan.append(raw)
            data.append(np.stack(format_chan))
    data = np.stack(data)
    return data
    
def run_nomads(data_dict):
    print("Beginning NOMADS Pipeline...")
    input_data = format_data(data_dict)
    try:
        results = pipeline(input_data)
    except:
        raise Exception("PSD or Synapsin Channel contained only one value. Exiting...")
    print("Finished NOMADS Pipeline.")
    return results
    
def upload_results(path, results_key):
    client = boto3.client('s3')
    s3 = boto3.resource('s3')
    s3_bucket_exists_waiter = client.get_waiter('bucket_exists')
    bucket = client.create_bucket(Bucket="nomads-unsupervised-results")
    s3_bucket_exists_waiter.wait(Bucket="nomads-unsupervised-results")

    bucket = s3.Bucket("nomads-unsupervised-results")
    bucket.Acl().put(ACL='public-read')
    files = glob.glob(path+"*")
    links_dict = {}
    for file in files:
        key = results_key + "/" + file.split("/")[-1]
        client.upload_file(file, "nomads-unsupervised-results", key)
        response = client.put_object_acl(ACL='public-read', Bucket="nomads-unsupervised-results", \
        Key=key)
        presigned_url = client.generate_presigned_url('get_object', Params={'Bucket': "nomads-unsupervised-results", 'Key': key}, ExpiresIn = 86400)
        links_dict[key] = presigned_url
    return links_dict

## PLEASE HAVE "/"" AT END OF PATH
## BETTER YET DONT TOUCH PATH
def driver(host, token, col, exp, z_range, y_range, x_range, path = "./results/"):
    
    print("Starting Nomads Unsupervised...")
    info = locals()
    data_dict, voxel_size = get_data(host, token, col, exp, z_range, y_range, x_range)
    
    results = run_nomads(data_dict)
    results = results.astype(np.uint8)
    np.putmask(results, results, 255)

    results_key = "_".join(["nomads-unsupervised", col, exp, "z", str(z_range[0]), str(z_range[1]), "y", \
    str(y_range[0]), str(y_range[1]), "x", str(x_range[0]), str(x_range[1])])
    
    pickle.dump(results, open(path + "nomads-unsupervised-predictions" + ".pkl", "wb"))
    print("Saved pickled results (np array) {} in {}".format("nomads-unsupervised-predictions.pkl", path))
    
    print("Generating PyMeda Plots...")
    
    norm_data = load_and_preproc(data_dict)
    try:
        pymeda_driver.pymeda_pipeline(results, norm_data, title = "PyMeda Plots on All Predicted Synapses", path = path)
    except:
        print("Not generating plots for all synapses, no predictions classified as Gaba")
    print("Uploading results...")
    #results = pickle.load(open("./results/nomads-unsupervised-predictions.pkl", "rb"))
    
    boss_links = boss_push(token, "collman_nomads", "nomads_predictions", z_range, y_range, x_range, {results_key: results})
    with open('results/NDVIS_links.csv', 'w') as csv_file:
        writer = csv.writer(csv_file)
        for key, value in boss_links.items():
            writer.writerow([key, value])
        
    
    s3_links = upload_results(path, results_key)
    
    
    print(s3_links)
    
    return info, results, s3_links, boss_links
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='NOMADS and PyMeda driver.')
    parser.add_argument('--host', required = True, type=str, help='BOSS Api host, do not include "https"')
    parser.add_argument('--token', required = True, type=str, help='BOSS API Token Key')
    parser.add_argument('--col', required = True, type=str, help='collection name')
    parser.add_argument('--exp', required = True, type=str, help='experiment name')
    parser.add_argument('--z-range', required = True, type=str, help='zstart,zstop   NO SPACES. zstart, zstop will be casted to ints')
    parser.add_argument('--y-range', required = True, type=str, help='ystart,ystop   NO SPACES. ystart, ystop will be casted to ints')
    parser.add_argument('--x-range', required = True, type=str, help='xstart,xstop   NO SPACES. xstart, xstop will be casted to ints')
    args = parser.parse_args()
    
    z_range = list(map(int, args.z_range.split(",")))
    y_range = list(map(int, args.y_range.split(",")))
    x_range = list(map(int, args.x_range.split(",")))
    
    driver(args.host, args.token, args.col, args.exp, z_range, y_range, x_range)
    
    