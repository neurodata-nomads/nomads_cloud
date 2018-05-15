# Cloud Computing Service for Synapse Detection
This repository contains a web service for running synapse detection algorithms on AWS. An example pipeline, Nomads-unsupervised is provided to demonstrate how to add new pipelines to this service. The Nomads-unsupervised directory also contains useful code for a fully integrating an algorithm with NDVis, BOSS, and PyMeda.

Installation Instructions:
0. Prerequisites: Have AWS-Cli (logged in) and Python3 installed on computer. Instructions on how to install AWS (here)[https://docs.aws.amazon.com/cli/latest/userguide/installing.html].
1. Enter the service directory and run "pip3 install -r requirements.txt"
2. Run "python3 server.py"
3. Go to http://localhost:8000

You should see a web form where you can submit synapse detection jobs to AWS batch. 

Documentation Links:
1. Service Documentation
2. Useful Modules for Synapse Pipelines
3. How to Add New Pipelines




