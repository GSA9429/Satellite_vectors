import datetime
from sgp4.api import Satrec, jday
import pyproj
from mpi4py import MPI
import pandas as pd
### function for converting the positions into lat, long and altitude
def ecef2lla(pos_x, pos_y, pos_z):
    ecef = pyproj.Proj(proj="geocent", ellps="WGS84", datum="WGS84")
    lla = pyproj.Proj(proj="latlong", ellps="WGS84", datum="WGS84")
    transformer = pyproj.Transformer.from_proj(ecef, lla)
    lon, lat, alt = transformer.transform(pos_x, pos_y, pos_z)
    return lon, lat, alt


### function for batch processing the TLEs and convert them to satellite data in forms of position and velocities
def process_satellite_batch(tle_lines, current_time, user_latitudes, user_longitudes):
    # for i in range(0, len(tle_lines)-1, 2):    
    #     satellites = [Satrec.twoline2rv(tle_lines[i], tle_lines[i+1])]
    satellites = [Satrec.twoline2rv(tle_lines[i], tle_lines[i+1]) for i in range(0, len(tle_lines)-1, 2)]
    results = []
    for sat in satellites:
        jd, fr = jday(current_time.year, current_time.month, current_time.day,
                      current_time.hour, current_time.minute, current_time.second)
        _, position, velocity = sat.sgp4(jd, fr)
        lon, lat, alt = ecef2lla(position[0], position[1], position[2])
        if min(user_latitudes) <= lat <= max(user_latitudes) and min(user_longitudes) <= lon <= max(user_longitudes):
            results.append((current_time, position[0], position[1], position[2], velocity[0], velocity[1], velocity[2], lon, lat, alt))
    return results

def main():
    tle_file = "27000sats.txt" ### input file for sats
    output_file = "satellite_positions.csv"  #### output file for sats data
    user_coordinates = [[90, 120], [90, -90], [-90, 150], [-90, -20]]  ###user input for 4 points of lats and longs

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if rank == 0:
        with open(tle_file, 'r') as file:
            tle_lines = file.readlines()
    else:
        tle_lines = None

    tle_lines = comm.bcast(tle_lines, root=0)
    num_tle_lines_per_process = len(tle_lines) // size

    start_time = datetime.datetime.now()
    end_time = start_time + datetime.timedelta(days=1) #### number of days to be inputted
    time_interval = datetime.timedelta(seconds=0.1) ### time interval to be inputted 
    user_latitudes = [coord[0] for coord in user_coordinates]
    user_longitudes = [coord[1] for coord in user_coordinates]

    results = []

    for current_time in pd.date_range(start=start_time, end=end_time, freq=time_interval):
        tle_batch = tle_lines[rank*num_tle_lines_per_process:(rank+1)*num_tle_lines_per_process]
        batch_results = process_satellite_batch(tle_batch, current_time, user_latitudes, user_longitudes)
        results.extend(batch_results)

    all_results = comm.gather(results, root=0)

    if rank == 0:
        merged_results = []
        for sublist in all_results:
            for item in sublist:
                merged_results.append(item)
        df = pd.DataFrame(merged_results, columns=["time", "P(x)", "P(y)", "P(z)", "V(x)", "V(y)", "V(z)", "Longitude", "Latitude", "Altitude"])
        df.to_csv(output_file, index=False)
        print("Data saved to", output_file)

if __name__ == "__main__":
    main()
