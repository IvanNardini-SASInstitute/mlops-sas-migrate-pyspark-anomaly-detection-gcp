# -*- coding: utf-8 -*-

"""
train.py is the training module for our project.
Remarks: The model package is designed in a way
it's executable both in SAS Viya and GCP Dataproc

Steps:
1 - Read data (both server and gcp cloud storage)
2 - Build Machine Learning Pipeline
3 - Serialize the Pipeline and all data

Author: Ivan Nardini (ivan.nardini@sas.com)
"""

# Libraries ------------------------------------------------------------------------------------------------------------
import logging
import logging.config
import argparse
import yaml

#from helpers import read_parquet, write_parquet, metrics, save_pipeline

import pyspark
from pyspark.sql.functions import col, lit, udf
from pyspark.sql.types import DoubleType
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler, MinMaxScaler
from pyspark.ml.classification import GBTClassifier
from pyspark.ml import Pipeline, PipelineModel

try:
    from pyspark import SparkContext, SparkConf
    from pyspark.sql import SparkSession
except ImportError as e:
    print('WARN: Something wrong with pyspark library. Please check configuration settings!')


# Helpers --------------------------------------------------------------------------------------------------------------

def read_parquet (session: SparkSession, filepath: str) -> pyspark.sql.DataFrame:
    '''
    Read a parquet file
    :param session: SparkSession
    :param filepath: the path of parquet datafile
    :return: pyspark.sql.DataFrame
    '''
    return session.read.parquet(filepath)


def write_parquet (df: pyspark.sql.DataFrame, filepath: str) -> None:
    '''
    Write a parquet file
    :param df: DataFrame to store
    :param filepath: the path of parquet datafile
    :return: None
    '''
    df.write.mode('overwrite').save(filepath)


def metrics (session: SparkSession, dataframe: pyspark.sql.DataFrame, actual: str,
             predicted: str) -> pyspark.sql.DataFrame:
    '''
    Calculates evaluation metrics from predicted results

    :param dataframe: spark.sql.dataframe with the real and predicted values
    :param actual: Name of column with observed target values
    :param predicted: Name of column with predicted values
    :return:
    '''

    # Along each row are the actual values and down each column are the predicted
    dataframe = dataframe.withColumn(actual, col(actual).cast('integer'))
    dataframe = dataframe.withColumn(predicted, col(predicted).cast('integer'))
    cm = dataframe.crosstab(actual, predicted)
    cm = cm.sort(cm.columns[0], ascending=True)

    # Adds missing column in case just one class was predicted
    if not '0' in cm.columns:
        cm = cm.withColumn('0', lit(0))
    if not '1' in cm.columns:
        cm = cm.withColumn('1', lit(0))

    # Subsets values from confusion matrix
    zero = cm.filter(cm[cm.columns[0]] == 0.0)
    first_0 = zero.take(1)

    one = cm.filter(cm[cm.columns[0]] == 1.0)
    first_1 = one.take(1)

    tn = first_0[0][1]
    fp = first_0[0][2]
    fn = first_1[0][1]
    tp = first_1[0][2]

    # Calculate metrics from values in the confussion matrix
    if (tp == 0):
        acc = float((tp + tn) / (tp + tn + fp + fn))
        sen = 0
        spe = float((tn) / (tn + fp))
        prec = 0
        rec = 0
        f1 = 0
    elif (tn == 0):
        acc = float((tp + tn) / (tp + tn + fp + fn))
        sen = float((tp) / (tp + fn))
        spe = 0
        prec = float((tp) / (tp + fp))
        rec = float((tp) / (tp + fn))
        f1 = 2 * float((prec * rec) / (prec + rec))
    else:
        acc = float((tp + tn) / (tp + tn + fp + fn))
        sen = float((tp) / (tp + fn))
        spe = float((tn) / (tn + fp))
        prec = float((tp) / (tp + fp))
        rec = float((tp) / (tp + fn))
        f1 = 2 * float((prec * rec) / (prec + rec))

    # Print results
    print('Confusion Matrix and Statistics: \n')
    cm.show()

    print('True Positives:', tp)
    print('True Negatives:', tn)
    print('False Positives:', fp)
    print('False Negatives:', fn)
    print('Total:', dataframe.count(), '\n')

    print('Accuracy: {0:.2f}'.format(acc))
    print('Sensitivity: {0:.2f}'.format(sen))
    print('Specificity: {0:.2f}'.format(spe))
    print('Precision: {0:.2f}'.format(prec))
    print('Recall: {0:.2f}'.format(rec))
    print('F1-score: {0:.2f}'.format(f1))

    # Create spark dataframe with results
    l = [(acc, sen, spe, prec, rec, f1)]
    df = session.createDataFrame(l, ['Accuracy', 'Sensitivity', 'Specificity', 'Precision', 'Recall', 'F1'])
    return df


extract0_udf = udf(lambda value: value[0].item(), DoubleType())
extract1_udf = udf(lambda value: value[1].item(), DoubleType())

def save_pipeline(pipeline: PipelineModel, filepath:str) -> None:
    '''
    Serialize the fitted pipeline
    :param pipeline:
    :param filepath:
    :return: None
    '''
    pipeline.write().overwrite().save(path=filepath)

# Builders -------------------------------------------------------------------------------------------------------------

def build_pipeline (pipeconfig: dict) -> pyspark.ml.Pipeline:
    '''
    Build a Pipeline instance based on config file
    :param pipeconfig: metadata dictionary
    :return: pyspark.ml.Pipeline
    '''

    # Pipeline metadata
    cats = pipeconfig['variables']['categoricals']
    nums = pipeconfig['variables']['numericals']
    index_names = pipeconfig['metadata']['index_names']
    encoded_names = pipeconfig['metadata']['encoded_names']
    vect_name = pipeconfig['metadata']['vect_name']
    feats_name = pipeconfig['metadata']['feats_name']
    labelcol = pipeconfig['model']['labelCol']
    maxdepth = pipeconfig['model']['maxDepth']
    maxbins = pipeconfig['model']['maxBins']
    maxiter = pipeconfig['model']['maxIter']
    seed = pipeconfig['model']['seed']

    # Build stages
    stageone = StringIndexer(inputCols=cats,
                             outputCols=index_names)

    stagetwo = OneHotEncoder(dropLast=False,
                             inputCols=stageone.getOutputCols(),
                             outputCols=encoded_names)

    stagethree = VectorAssembler(inputCols=nums + stagetwo.getOutputCols(),
                                 outputCol=vect_name)

    stagefour = MinMaxScaler(inputCol=stagethree.getOutputCol(),
                             outputCol=feats_name)

    stagefive = GBTClassifier(featuresCol=stagefour.getOutputCol(),
                              labelCol=labelcol,
                              maxDepth=maxdepth,
                              maxBins=maxbins,
                              maxIter=maxiter,
                              seed=seed)
    pipeline = Pipeline(stages=[stageone, stagetwo, stagethree, stagefour, stagefive])

    return pipeline

# Main -----------------------------------------------------------------------------------------------------------------

def run_training (args):

    # Read configuration
    logging.info('Read config file.')
    with open(args.configfile, "r") as cf:
        config = yaml.load(cf, Loader=yaml.FullLoader)
    sparksession = config['sparksession']
    data = config['data']
    pipeline = config['pipeline']
    output = config['output']

    # Create a spark session
    logging.info('Instantiate the {0} Spark session'.format(sparksession['appName']))
    spark = SparkSession.builder \
        .master(sparksession['master']) \
        .appName(sparksession['appName']) \
        .getOrCreate()

    # Load Data
    logging.info('Load train and test data')
    train_df = read_parquet(spark, data['train_datapath'])
    test_df = read_parquet(spark, data['test_datapath'])

    # Execute training
    logging.info('Train {0} Pipeline'.format(pipeline['model']['method']))
    train_pipe = build_pipeline(pipeline)
    gbt_model = train_pipe.fit(train_df)

    # Evaluate
    logging.info('Evaluate the model')
    predictions_test = gbt_model.transform(test_df)
    predictions_test.select(output['showschema_train']).show(5)
    metrics_df = metrics(spark, predictions_test, 'Unusual', 'prediction')

    # Save training data
    logging.info('Save all the process outputs')
    # Save trained pipeline
    logging.info('Saving pipeline...')
    save_pipeline(gbt_model, output['pipeline_path'])
    # Save predictions
    logging.info('Saving predictions...')
    predictions_test_fmt = predictions_test.withColumn('P_Unusual0', extract0_udf('probability')).withColumn(
         'P_Unusual1', extract1_udf('probability')).select(output['columnschema_train'])
    write_parquet(predictions_test_fmt, output['test_scored_path'])
    # Save metrics
    logging.info('Saving metrics...')
    write_parquet(metrics_df, output['metrics_scored_path'])


if __name__ == "__main__":
    #logging.config.fileConfig("../../config/logging/local.conf")
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)
    logger = logging.getLogger(__name__)
    parser = argparse.ArgumentParser(description="Train Pyspark GBTClassifier")
    parser.add_argument('--configfile', required=True, help='path to configuration yaml file')
    args = parser.parse_args()
    run_training(args)
