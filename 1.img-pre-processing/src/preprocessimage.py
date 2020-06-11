import json
import boto3
import os
from botocore.exceptions import ClientError

# define rekognition client and environment variables
'''
"model_arn" to the ARN of the model that you want to start.
"project_arn" to the ARN of the project that contains the model that you want to use.
"version_name" to the name of the model that you want to start.
"min_inference_units" to the number of inference units that you want to use.
'''
client = boto3.client('rekognition')
model_arn = os.environ['REKOGNITION_MODEL_ARN']
# TODO: hardcoded
project_arn='arn:aws:rekognition:us-east-1:077546553367'
version_name='unicorn-gym-custom-label.2020-06-08T13.55.38'
min_inference_units=1

# define lambda client and environment variables
lambda_client = boto3.client('lambda')
lambda_arn = os.environ['LAMBDA_ENHANCED_IMAGE_ARN']

# method for enhancement image
def enhancedment_image(labels, bucket, photo):
    label_name = labels[0]['Name']
    confidence_score = labels[0]['Confidence']
    if label_name == 'bad':
        enhanced_response = lambda_client.invoke(FunctionName=lambda_arn,Payload=json.dumps({'bucket':bucket, 'imageName':photo}))
        res_dict = json.loads(enhanced_response['Payload'].read().decode())
        if res_dict['after']['label'] == "good":
            labels_bak = [{'Name': res_dict['after']['label'], 'Confidence': res_dict['after']['confidence']}]

# simpify return results
def return_result_format(error_code, body_str):
    return {'statusCode': error_code,'body': body_str}

# main event handler
def lambda_handler(event, context):
    # define payload inputs
    try:
        photo=event['queryStringParameters']['image']
        bucket=event['queryStringParameters']['bucket']
    except KeyError as ke:
        return return_result_format(400, 'Missing field {}, please check your input payload.'.format(ke))
    
    # TODO: logging output
    print("request event is ->****")
    print(event)
    print("bucket passed as query string: " + bucket)
    print("image passed as query string: " + photo)
    
    # starting rekognition custom label model
    try:
        print('Will try to start model: ' + model_arn)
        response=client.start_project_version(ProjectVersionArn=model_arn, MinInferenceUnits=min_inference_units)
        # wait for the model to be in the running state
        project_version_running_waiter = client.get_waiter('project_version_running')
        project_version_running_waiter.wait(ProjectArn=project_arn, VersionNames=[version_name])

        # get the running status
        describe_response=client.describe_project_versions(ProjectArn=project_arn, VersionNames=[version_name])
        for model in describe_response['ProjectVersionDescriptions']:
            print("Status: " + model['Status'])
            print("Message: " + model['StatusMessage']) 
    except ClientError as ce:
        # this is expected exception, let it pass.
        if ce.response['Error']['Code'] == 'ResourceInUseException':
            print("The model is already running: " + model_arn)
    except Exception as e:
        return return_result_format(500, "Unknown exception: {}".format(e))

    # process using S3 object
    minimum_confidence = 50
    try:
        response = client.detect_custom_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
            MinConfidence=minimum_confidence,
            ProjectVersionArn=model_arn)
        labels=response['CustomLabels']
    except ClientError as ce:
        if ce.response['Error']['Code'] == 'InvalidS3ObjectException':
            return return_result_format(400, 'Invalid S3 object location \'s3://{}/{}\', please check your value of payload.'.format(bucket,photo))
    except Exception as e:
        return return_result_format(400, 'Input error {}, please check your value of payload.'.format(e))
    
    # return good result
    return return_result_format(200, json.dumps(labels))
