# degrees

Calculate degrees of separation.  

## Workings  
Calculates degrees of separation between any two Wikipedia URLS. It uses two queues to manage and work its way through.  

get_links() scrapes and obtains a list of URLS. It removes any URLS that are not in the WIKIPEDIA domain.  
explore() holds the logic of how the worker processes computes the degree in a Breadth First Search way.  
get_degrees() seeds the queue and starts off the worker processes.  

It is important to note that there may be more than one path to a Target URI. For example:  
1. Tom Cruise > Dustin Hoffman > Kevin Bacon  
2. Tom Cruise > A few good men > Kevin Bacon  

This algorithm returns the degree of separation of the first link that it obtains between the
Start and Target URIs. It may not be the smallest degree of separation in every case.  


## Running  
Clone and cd into the directory. After that, execute the following:
```
virtualenv -p python3 env  
source env/bin/activate  
pip install -r requirements.txt  
python degrees.py  

# You can change the start and target uris from the command line like this:  
python degrees.py --start=https://en.wikipedia.org/wiki/Tom_Cruise --target=https://en.wikipedia.org/wiki/Kevin_Bacon  
```
Defaults:  
* start=https://en.wikipedia.org/wiki/A_Few_Good_Men  
* target=https://en.wikipedia.org/wiki/Kevin_Bacon  


## Testing  
```
pip install -r tests-requirements.txt  
py.test .  
```
