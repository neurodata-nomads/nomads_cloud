from flask import Flask, flash, render_template, url_for, \
request, redirect
import boto3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pickle

SENDER = 'NOMADSPipeline@gmail.com'
PASSWORD = pickle.load(open("password.pkl", "rb"))


def send_email(url, recipient, pipeline):

    #text = "Hi!\nHere is the link for Nomads Unsupervised results:\n{}}".format("url")
    html = """\
    <html>
      <head></head>
      <body>
        <p>Hi!<br>
           Here is the <a href="{}">link</a> to {} Results.
        </p>
      </body>
    </html>
    """.format(url, pipeline)

    msg = MIMEText(html, "html")

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER, PASSWORD)
    server.sendmail(SENDER, recipient, msg.as_string())
    server.quit()


app = Flask(__name__)

def submit_job(email, pipeline, token, col, exp, z_range, y_range, x_range):

    try:
        z_range_proc = list(map(int, z_range.split(",")))
        y_range_proc = list(map(int, y_range.split(",")))
        x_range_proc = list(map(int, x_range.split(",")))
    except:
        print("Job not submitted, dimensions not correctly formmated")

    job_name = "_".join([pipeline, col, exp, "z", str(z_range_proc[0]), str(z_range_proc[1]), "y", \
    str(y_range_proc[0]), str(y_range_proc[1]), "x", str(x_range_proc[0]), str(x_range_proc[1])])

    client = boto3.client('s3')

    s3_bucket_exists_waiter = client.get_waiter('bucket_exists')

    if pipeline == "nomads-unsupervised":
        bucket = client.create_bucket(Bucket="nomads-unsupervised-results")
        s3 = boto3.resource("s3")
        bucket = s3.Bucket("nomads-unsupervised-results")
        bucket.Acl().put(ACL='public-read')

        url = "https://s3.console.aws.amazon.com/s3/buckets/nomads-unsupervised-results/{}/?region=us-east-1&tab=overview".format(job_name)
        send_email(url, email, pipeline)

    if pipeline == "nomads-classifier":
        bucket = client.create_bucket(Bucket="nomads-classifier-results")
        s3 = boto3.resource("s3")
        bucket = s3.Bucket("nomads-classifier-results")
        bucket.Acl().put(ACL='public-read')

        url = "https://s3.console.aws.amazon.com/s3/buckets/nomads-classifier-results/{}/?region=us-east-1&tab=overview".format(job_name)
        send_email(url, email, pipeline)


    client = boto3.client("batch")
    response = client.describe_compute_environments(
        computeEnvironments=[
            'nomads-ce',
        ],
    )
    if len(response["computeEnvironments"]) == 0:
        response = client.create_compute_environment(
            type='MANAGED',
            computeEnvironmentName='nomads-ce',
            computeResources={
                'type': 'EC2',
                'desiredvCpus': 0,
                'instanceRole': 'ecsInstanceRole',
                'instanceTypes': [
                    "optimal"
                ],
                'maxvCpus': 20,
                'minvCpus': 0,
                'securityGroupIds': [
                    'sg-41927a3e',
                ],
                'subnets': [
                    'subnet-11dc531d',
                    'subnet-17c65f72',
                    'subnet-75006549',
                    'subnet-4e2ace06',
                    'subnet-7ca59151',
                    'subnet-74f3d02f'
                ],
                'tags': {
                    'Name': 'Batch Instance - C4OnDemand',
                },
            },
            serviceRole='AWSBatchServiceRole',
            state='ENABLED',
        )

    response = client.describe_job_queues(jobQueues=["nomads-queue"])
    if len(response["jobQueues"]) == 0:
        response = client.create_job_queue(
            jobQueueName='string',
            state='ENABLED',
            priority=10,
            computeEnvironmentOrder=[
                {
                    'order': 1,
                    'computeEnvironment': 'nomads-ce'
                },
            ]
        )

    response = client.describe_job_definitions(
        jobDefinitionName=pipeline,
        status='ACTIVE',
    )
    if len(response["jobDefinitions"]) == 0:
        if pipeline == "nomads-unsupervised":
            register_nomads_unsupervised(client)
        if pipeline == "nomads-classifier":
            register_nomads_classifier(client)
    response = client.submit_job(
        jobName=job_name,
        jobQueue='nomads-queue',
        jobDefinition=pipeline,
        containerOverrides={
            'vcpus': 1,
            'memory': 2000,
            'command': [
                "python3",
                "driver.py",
                "--host",
                "api.boss.neurodata.io",
                "--token",
                token,
                "--col",
                col,
                "--exp",
                exp,
                "--z-range",
                z_range,
                "--x-range",
                x_range,
                "--y-range",
                y_range
            ],
        },
    )
    print(job_name)
    return job_name

def register_nomads_unsupervised(client):
    response = client.register_job_definition(
        type='container',
        containerProperties={
            'command': [
                "echo",
                "Staring Container"
            ],
            'image': '389826612951.dkr.ecr.us-east-1.amazonaws.com/nomads-unsupervised',
            'memory': 4000,
            'vcpus': 1,
        },
        jobDefinitionName="nomads-unsupervised",
    )

def register_nomads_classifier(client):
    response = client.register_job_definition(
        type='container',
        containerProperties={
            'command': [
                "echo",
                "Staring Container"
            ],
            'image': "389826612951.dkr.ecr.us-east-1.amazonaws.com/nomads-classifier",
            'memory': 4000,
            'vcpus': 1,
        },
        jobDefinitionName="nomads-classifier",
    )

@app.route("/", methods = ["GET"])
def index():
    client = boto3.client("batch")
    return render_template("index.html")

@app.route("/submit", methods = ["GET", "POST"])
def submit():
    token = request.form["token"]
    col = request.form["col"]
    exp = request.form["exp"]
    z_range = request.form["z_range"].replace(" ", "")
    y_range = request.form["y_range"].replace(" ", "")
    x_range = request.form["x_range"].replace(" ", "")

    pipeline = request.form["pipeline"]
    email = request.form["email"]
    host = "api.boss.neurodata.io"
    submit_job(email, pipeline, token, col, exp, z_range, y_range, x_range)


    return redirect(url_for("index"))

@app.route("/complete", methods = ["GET", "POST"])
def complete():
    pass

if __name__ == "__main__":
    #send_email("blah", "brandonduderstadt@gmail.com")
    #submit_job("edef359a8de270163c911dcef5d467a72348d68d", "collman", "M247514_Rorb_1_light", "40,45", "6500,7000", "6500,7000")
    app.run(debug = True, port = 8000, threaded = True)
