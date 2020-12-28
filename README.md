# Migrating existing analytics Spark workloads on Google Cloud Platform with SAS 

Nowadays migrating on-premise existing BigData workloads on the cloud is one of the main
customer's challenges.

Based on our experience, it is really complicated for several reasons. 
For example, Data Scientists does not know what is needed to allow their models 
running in the cloud. Or IT and Business is struggling to define a organization process
in respect of compliance and governance.

With this project, we want to show how SAS can support migrating analytics on 
Google Cloud Platform providing business process and governance by SAS Model Manager 
and SAS Workflow Manager

## Overview 

Below the on-premise application architecture of the solution:

<p align="center">
<img src="https://github.com/IvanNardini/mlops_sas_gcp_spark/raw/master/mm_gcp_final.png">
</p>

## Scenario Description

In the as-is: 

Data Scientist submits pyspark job to Hadoop-Spark cluster on premise. 

Then migration starts: 

1. Data Scientist creates several pyspark model packages. And he registers different versions in SAS® Model Manager 
using [SAS® sasctl](https://github.com/sassoftware/python-sasctl).

2. Big Data Engineer maps on-prem cluster configuration and create a templates. 

3. DevOps engineer may create cloud functions to deploy the cluster (and submit train and score jobs) on Google Cloud Platform

4. Once the workflow starts, each actor involved in the process claims and completes user tasks. 
In this case, a Validator approve the Champion model. And an IT provides
Cloud bucket name for migration. When the model is migrated on predefined Cloud storage bucket, 
either Big Data Engineer or DevOps receive a notification.

5. Then, a new model training is processed in an ephemeral Cloud Dataproc and the trained pipeline is stored ready to score new data.
For sick of simplicity, a final user loads parquet files to score in the predefined Cloud Storage bucket.
A new scoring process is triggered by Cloud function and scored data are stored in the same
Cloud Storage bucket.

## Installation

### Server FS side

1. Clone the project.

2. Create virtual environment 

    ```bash
    cd mlops_sas_gcp_spark/
    python3 -m venv env
    source env/bin/activate
    pip install --file requirements.txt
    source deactivate
    ```
3. Create a folder for Viya logs

    ```bash
    mkdir logs
    ```

4. Change group ownership based on SAS Workflow Administration group.
For example, if you have SAS Workflow Administration group called CASHostAccountRequired, 
run 

    ```bash
    chown -R sas:CASHostAccountRequired mlops_sas_gcp_spark/
    ```
### SAS Viya side

1. Import [ModelOps for GCP](src/workflow/definition/) in SAS Workflow Manager

2. Import [run_build.sas](src/workflow/definition/run_build.sas) and [run_migrate.sas](src/workflow/definition/run_migrate.sas)
jobs in SAS Job Execution

**Notice: Don't forget to double checks RESTAPIs endpoints in the workflow definition service tasks and 
paths in the jobs**

### Google Cloud Platform side

You have to create a service account and generate a key
for authentication as shown [here](https://cloud.google.com/docs/authentication/getting-started#auth-cloud-implicit-python).

Then you have to enable all APIs you need:

* Cloud Dataproc 
* Cloud Logging 
* Cloud Functions 
* Cloud Storage

If everything is correct, you can move on and 

1. Create a bucket named **network-spark-migrate**

2. Create these Cloud functions: **batch-train** and **batch-score**

Please look at [cloud functions images folder](docs/images/cloud_functions/batch-train1.JPG)
as reference.

All code associated to cloud functions is under [cloudfunction folder](src/cloudfunction/batch_train/batch_train.py).

## Usage

From SAS Model Manager project, start ModelOps for GCP workflow and user tasks one by one.

If everything is correct, once you migrate the model, batch-train cloud function is triggered.
It creates an ephemeral Dataproc cluster for training the model.
Once the training ends, the train cluster is deleted and you get a
new model ready for scoring.

Assuming that you receive a scoring request, you can upload [parquet files](data/processed/ML-MATT-CompetitionQT1920_val_processed.parquet).
The batch-score cloud function is triggered. It creates an ephemeral Dataproc cluster for scoring data and deletes it 
once it finishes. 

## Contributing
Feedbacks and Pull requests are welcome. 

For major changes, please reach out both [me](https://www.linkedin.com/in/ivan-nardini/) or 
[Artem Glazkov, SAS Russia](https://www.linkedin.com/in/artem-glazkov-80753824/)