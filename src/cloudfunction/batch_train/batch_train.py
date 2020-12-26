# -*- coding: utf-8 -*-

"""
batch_train.py is the module for create an
ephemeral Dataproc and train the model in batch.

Steps:
1 - Create a custom Dataproc Cluster
2 - Train the model
3 - Delete the cluster

Look at documentation from GCP
Author: Ivan Nardini (ivan.nardini@sas.com)
"""

# Libraries ------------------------------------------------------------------------------------------------------------
import logging
import logging.config
import time
from google.cloud import dataproc_v1 as dataproc

# Helpers --------------------------------------------------------------------------------------------------------------

def check_if_cluster (project_id, cluster_name, region):
    '''
    Check if cluster already exists
    :param project_id:
    :param cluster_name:
    :param region:
    :return:
    '''

    # Create a client with the endpoint set to the desired cluster region.
    cluster_client = dataproc.ClusterControllerClient(
        client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
    )

    try:
        return cluster_client.get_cluster(project_id, region, cluster_name)
    except RuntimeError as message:
        return None

def create_cluster (project_id, cluster_name, bucket_name, region, zone, pip_packages):
    '''
    Create a Cloud Dataproc cluster
    :param project_id: The name of project to use for creating resources.
    :param cluster_name: The name of cluster
    :param bucket_name: The name of bucket
    :param region: The name of the region
    :param zone: The name of zone
    :param pip_packages: The list of packages to install
    :return: result
    '''

    # Create a client with the endpoint set to the desired cluster region.
    cluster_client = dataproc.ClusterControllerClient(
        client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
    )

    # Create the cluster config.
    # gcloud beta dataproc clusters create train-spark-demo --bucket network-spark-migrate
    # --region europe-west6 --subnet default --zone europe-west6-b --master-machine-type n1-standard-4
    # --master-boot-disk-size 500 --num-workers 2 --worker-machine-type n1-standard-4 --worker-boot-disk-size 500
    # --image-version preview-debian10 --scopes 'https://www.googleapis.com/auth/cloud-platform'
    # --initialization-actions 'gs://goog-dataproc-initialization-actions-europe-west6/python/pip-install.sh'
    # --metadata PIP_PACKAGES="PyYAML==5.3.1 numpy==1.19.4 pandas==1.1.4 pyspark==3.0.1" --project sas-ivnard
    cluster = {
        "project_id": project_id,
        "cluster_name": cluster_name,
        "config": {
            "config_bucket": bucket_name,
            "gce_cluster_config": {
                "service_account_scopes": [
                    "https://www.googleapis.com/auth/cloud-platform"
                ],
                "network_uri": "default",
                "subnetwork_uri": "",
                # "internal_ip_only": false,
                "zone_uri": zone,
                "metadata": {
                    "PIP_PACKAGES": pip_packages
                },
            },
            "master_config": {
                "num_instances": 1,
                "machine_type_uri": "n1-standard-4",
                "disk_config": {
                    "boot_disk_type": "pd-standard",
                    "boot_disk_size_gb": 500,
                    "num_local_ssds": 0
                },
            },
            "software_config": {
                "image_version": "preview-debian10",
            },
            "initialization_actions": [
                {
                    "executable_file": "gs://goog-dataproc-initialization-actions-europe-west6/python/pip-install.sh"
                }
            ],
            "worker_config": {
                "num_instances": 2,
                "machine_type_uri": "n1-standard-4",
                "disk_config": {
                    "boot_disk_type": "pd-standard",
                    "boot_disk_size_gb": 500,
                    "num_local_ssds": 0
                },
            },
            "secondary_worker_config": {
                "num_instances": 0
            },
            # "endpointConfig": {
            #     "enableHttpPortAccess": false
            # }
        }
    }

    # Create the cluster.
    cluster = cluster_client.create_cluster(
        request={"project_id": project_id, "region": region, "cluster": cluster}
    )
    result = cluster.result()
    # Output a success message.
    logging.info(f"Cluster {result.cluster_name} created successfully!")
    return cluster

def check_job_state (project_id, region, job_id):
    '''
    Check Job state
    :param project_id: The name of project to use for creating resources.
    :param region: The name of the region
    :param job_id: The name of the job
    :return: job_state: A string with job state
    '''

    # Create the job client.
    job_client = dataproc.JobControllerClient(client_options={
        'api_endpoint': '{}-dataproc.googleapis.com:443'.format(region)
    })

    job_instance = job_client.get_job(
        request={"project_id": project_id, "region": region, "job_id": job_id}
    )
    job_state = str.lower(str(job_instance.status.state))

    return job_state

def submit_train_job (project_id, cluster_name, region, job_id):
    '''
    Submit batch train job
    :param project_id: The name of project to use for creating resources.
    :param cluster_name: The name of cluster
    :param region: The name of the region
    :param job_id: The name of the job
    :return: None
    '''
    # Create the job client.
    job_client = dataproc.JobControllerClient(client_options={
        'api_endpoint': '{}-dataproc.googleapis.com:443'.format(region)
    })

    # Create the job config.
    # gcloud dataproc jobs submit pyspark gs://network-spark-migrate/model/train.py --cluster train-spark-demo
    # --region europe-west6 --files=gs://network-spark-migrate/model/demo-config.yml -- --configfile ./demo-config.yml
    job = {
        'reference': {
            'project_id': project_id,
            'job_id': job_id
        },
        'placement': {
            'cluster_name': cluster_name
        },
        'pyspark_job': {
            'main_python_file_uri': 'gs://network-spark-migrate/model/train.py',
            'file_uris': ['gs://network-spark-migrate/model/demo-config.yml'],
            'args': ['--configfile', './demo-config.yml']
        }
    }

    job_instance = job_client.submit_job(
        request={"project_id": project_id, "region": region, "job": job}
    )

    job_reference = str.lower(str(job_instance.reference.job_id))
    job_state = str.lower(str(job_instance.status.state))
    print(job_state)
    # if job_state != 'done':
    #     logging.info(f"Job {job_reference} finished successfully!")

def delete_cluster (project_id, cluster_name, region):
    '''
    Delete train cluster
    :param project_id: The name of project to use for creating resources.
    :param cluster_name: The name of cluster
    :param region: The name of the region
    :return: None
    '''

    # Create a client with the endpoint set to the desired cluster region.
    cluster_client = dataproc.ClusterControllerClient(
        client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
    )

    operation = cluster_client.delete_cluster(
        request={"project_id": project_id, "region": region, "cluster_name": cluster_name}
    )

    result = operation.result()
    print(result)
    # Output a success message.
    logging.info(f"Cluster deletes successfully!")


def main (event, context):
    '''
    Triggered by a change to a Cloud Storage bucket.
    :param event:
    :param context:
    :return:
    '''

    # Variables
    PROJECT_ID = 'sas-ivnard'
    CLUSTER_NAME = 'train-spark-demo'
    BUCKET_NAME = 'network-spark-migrate'
    REGION = 'europe-west6'
    ZONE = 'europe-west6-b'
    PIP_PACKAGES = "PyYAML==5.3.1 numpy==1.19.4 pandas==1.1.4 pyspark==3.0.1"
    JOB_ID = 'Batch_Train_Model'

    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

    # Create a client with the endpoint set to the desired cluster region.
    cluster_client = dataproc.ClusterControllerClient(
        client_options={"api_endpoint": f"{REGION}-dataproc.googleapis.com:443"}
    )

    # Because we upload several files in a loop, the function will be trigger n times where
    # n is the number of files uploaded. We need to create a filter.
    logging.info(event['name'])
    if event['name'] == 'model/train.py':
        logging.info(f"Creating cluster {CLUSTER_NAME}...")
        cluster = create_cluster(PROJECT_ID, CLUSTER_NAME, BUCKET_NAME, REGION, ZONE, PIP_PACKAGES)
        logging.info(f"Submitting job {JOB_ID}...")
        cluster.add_done_callback(lambda _: submit_train_job(PROJECT_ID, CLUSTER_NAME, REGION, JOB_ID))
        # while check_job_state(PROJECT_ID, REGION, JOB_ID) != 'done':
        #     logging.info(f"Job {JOB_ID} is running...")
        #     time.sleep(5)
        # logging.info(f"Job {JOB_ID} is {check_job_state(PROJECT_ID, REGION, JOB_ID)}")
        # logging.info(f"Deleting cluster {CLUSTER_NAME}...")
        # delete_cluster(PROJECT_ID, CLUSTER_NAME, REGION)
