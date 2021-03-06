# Cloud Computing Service for Synapse Detection
This repository contains a web service for running synapse detection algorithms on AWS. An example pipeline, Nomads-unsupervised is provided to demonstrate how to add new pipelines to this service. The Nomads-unsupervised directory also contains useful code for a fully integrating an algorithm with NDVis, BOSS, and PyMeda.

Installation Instructions:  
0.1 Prerequisites: Have AWS-Cli (logged in) and Python3 installed on computer.  
Instructions on how to install into AWS [here](https://docs.aws.amazon.com/cli/latest/userguide/installing.html).  
Instructions on how to log into AWS [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html).

1. Enter the service directory and run "pip3 install -r requirements.txt"
2. Run "python3 server.py"
3. Go to http://localhost:8000

You should see a web form where you can submit synapse detection jobs to AWS batch.  
**Important Note:** In order to push results to BOSS, the API Key you provide on the form must have permissions to push to the channel "collman_nomads" and the experiment "nomads_predictions".

Documentation Links:
1. [Web Service Documentation](https://nbviewer.jupyter.org/github/neurodata-nomads/nomads_cloud/blob/master/docs/Web%20Service%20Documentation.ipynb)
2. [Useful Modules for Synapse Pipelines](https://nbviewer.jupyter.org/github/neurodata-nomads/nomads_cloud/blob/master/docs/Useful%20Modules%20for%20Synapse%20Pipelines.ipynb)




