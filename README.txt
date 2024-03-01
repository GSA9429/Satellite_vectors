This program is designed to read the satellite data in form TLEs, and then convert them to state vectors such as positions and velocity vectors in x,y,z.

After that when we have them, we convert them to lat and long data along with alitude, using pyproj module.

After that a filter has been added upon to filter the position of satellites , in between the user defined lats and longs.

And the whole code was parallelized using MPI, to inlcude 27000 sats data.