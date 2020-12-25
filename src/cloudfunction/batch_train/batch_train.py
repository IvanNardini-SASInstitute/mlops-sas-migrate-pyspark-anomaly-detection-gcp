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

# Libraries
from google.cloud import dataproc_v1 as dataproc

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
    operation = cluster_client.create_cluster(
        request={"project_id": project_id, "region": region, "cluster": cluster}
    )
    result = operation.result()

    # Output a success message.
    print(f"Cluster created successfully: {result.cluster_name}")

def main(event, context):
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

    create_cluster(PROJECT_ID, CLUSTER_NAME, BUCKET_NAME, REGION, ZONE, PIP_PACKAGES)