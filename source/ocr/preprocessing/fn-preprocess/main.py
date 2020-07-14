"""Lambda function to apply a 2-class good/bad Rekognition Custom Labels classifier to an S3 image
"""

# Python Built-Ins:
import json
import boto3
import os

# External Dependencies:
from botocore.exceptions import ClientError

rekognition = boto3.client("rekognition")


model_arn = os.environ["REKOGNITION_MODEL_ARN"]
# TODO: Parameterize model details
project_arn="arn:aws:rekognition:us-east-1:077546553367"
version_name="unicorn-gym-custom-label.2020-06-08T13.55.38"
min_inference_units=1

LABEL_CLASSES = ("bad", "good")  # Other labels outside this set will be ignored
ACCEPTABLE_CLASSES = ("good",)  # Any other LABEL_CLASSES labels are deemed unacceptable/"bad"


class MalformedRequest(ValueError):
    pass

class ModelError(ValueError):
    pass

class PoorQualityImage(ValueError):
    pass


# TODO: Either integrate this orphaned enhancement logic or remove it
def enhancedment_image(labels, bucket, photo):
    """method for enhancement image"""
    # define lambda client and environment variables
    lambda_client = boto3.client('lambda')
    lambda_arn = os.environ['LAMBDA_ENHANCED_IMAGE_ARN']
    
    label_name = labels[0]['Name']
    confidence_score = labels[0]['Confidence']
    if label_name == 'bad':
        enhanced_response = lambda_client.invoke(FunctionName=lambda_arn,Payload=json.dumps({'bucket':bucket, 'imageName':photo}))
        res_dict = json.loads(enhanced_response['Payload'].read().decode())
        if res_dict['after']['label'] == "good":
            labels_bak = [{'Name': res_dict['after']['label'], 'Confidence': res_dict['after']['confidence']}]

def handler(event, context):
    try:
        bucket = event["Bucket"]
        photo = event["Key"]
    except KeyError as ke:
        raise MalformedRequest(f"Missing field {ke}, please check your input payload")

    # TODO: logging output instead of prints
    print(f"Analyzing s3://{bucket}/{photo}")

    # Check the Rekognition Custom Labels model is running and start it if not:
    try:
        # TODO: Move this to Lambda init, or maybe ditch entirely?
        print(f"Trying to start Rekognition model {model_arn}")
        response=rekognition.start_project_version(
            ProjectVersionArn=model_arn,
            MinInferenceUnits=min_inference_units
        )
        # wait for the model to be in the running state
        project_version_running_waiter = rekognition.get_waiter("project_version_running")
        project_version_running_waiter.wait(ProjectArn=project_arn, VersionNames=[version_name])

        # For debugging/logging purposes only, show the active versions:
        describe_response = rekognition.describe_project_versions(
            ProjectArn=project_arn,
            VersionNames=[version_name]
        )
        model = next(describe_response["ProjectVersionDescriptions"])
        print(f"{model['Status']}: {model['StatusMessage']}\n{model_arn} version {version_name}")
    except ClientError as ce:
        if ce.response["Error"]["Code"] == "ResourceInUseException":
            # This is expected - let it pass
            print(f"Model is already running: {model_arn}")
        else:
            raise ModelError(f"ClientError while accessing Rekognition model: {ce}")
    except Exception as e:
        raise ModelError(f"Unknown exception accessing Rekognition model: {e}")

    # Analyze the image in S3:
    # TODO: Parameterize min confidence?
    minimum_confidence = 50
    try:
        labels = rekognition.detect_custom_labels(
            Image={ "S3Object": { "Bucket": bucket, "Name": photo } },
            MinConfidence=minimum_confidence,
            ProjectVersionArn=model_arn,
        )["CustomLabels"]
    except ClientError as ce:
        if ce.response["Error"]["Code"] == "InvalidS3ObjectException":
            raise MalformedRequest(
                f"Invalid S3 object location 's3://{bucket}/{photo}', please check your request'"
            )
        else:
            raise ModelError(f"ClientError while querying Rekognition model: {ce}")
    except Exception as e:
        raise ModelError(f"Unknown exception querying Rekognition: {e}")

    # Judge the image from the returned labels:
    print(labels)
    if not len(labels):
        raise PoorQualityImage(f"Model returned no labels")
    try:
        # Labels are sorted by desc confidence anyway, so first instance of recognised class = most confident
        toplabel = next(label for label in labels if label["Name"] in LABEL_CLASSES)
    except StopIteration:
        raise ModelError(f"Model returned {len(labels)} labels, but none in expected list {LABEL_CLASSES}")

    # Note we return an S3 location or an error (rather than a 'yes/no') because it's common for
    # pre-processing to *enhance* the image (e.g. skew/blur/lighting/cropping corrections) rather than simply
    # categorizing it - so this interface makes that functionality easier to add.
    if toplabel["Name"] in ACCEPTABLE_CLASSES:
        return {
            "Bucket": bucket,
            "Key": photo,
            "S3Uri": f"s3://{bucket}/{photo}",
            "TopLabel": toplabel,
            # Since the Step Function is initialized by S3 trigger we don't have that much control over the
            # initial data structure. Therefore this function (the first in the flow) will also return all
            # the initial input fields that we want to keep through the execution, and the SFn will fully
            # overwrite the state with this result rather than just adding it in somewhere:
            "Input": {
                "Bucket": bucket,
                "Key": photo,
                "S3Uri": f"s3://{bucket}/{photo}"
            }
        }
    else:
        raise PoorQualityImage(f"Image unacceptable: Labelled as '{toplabel['Name']}'")
