"""Lambda function to apply a 2-class good/bad Rekognition Custom Labels classifier to an S3 image
"""

# Python Built-Ins:
import json
import boto3
import os

# External Dependencies:
from botocore.exceptions import ClientError

rekognition = boto3.client("rekognition")
ssm = boto3.client("ssm")

default_model_arn_param = os.environ.get("REKOGNITION_MODEL_ARN_PARAM")
min_inference_units = int(os.environ.get("REKOGNITION_MIN_INFERENCE_UNITS", 1))

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

    if "RekognitionModelArn" in event:
        model_arn = event["RekognitionModelArn"]
    elif default_model_arn_param is not None:
        model_arn = ssm.get_parameter(Name=default_model_arn_param)["Parameter"]["Value"]
        if (not model_arn) or model_arn.lower() in ("undefined", "null"):
            raise MalformedRequest(
                "Neither request RekognitionModelArn nor expected SSM parameter are set. Got: "
                f"{default_model_arn_param} = '{model_arn}'"
            )
    else:
        raise MalformedRequest(
            "Neither request RekognitionModelArn nor env var REKOGNITION_MODEL_ARN_PARAM specified"
        )

    # TODO: logging output instead of prints
    print(f"Analyzing s3://{bucket}/{photo}")

    # Analyze the image in S3:
    # TODO: Parameterize min confidence?
    minimum_confidence = 50
    try:
        labels = rekognition.detect_custom_labels(
            Image={ "S3Object": { "Bucket": bucket, "Name": photo } },
            MinConfidence=minimum_confidence,
            ProjectVersionArn=model_arn,
        )["CustomLabels"]
    except rekognition.exceptions.ResourceNotFoundException:
        raise ModelError(f"Resource not found: Check your Rekognition Custom Labels model ARN {model_arn}")
    except rekognition.exceptions.ResourceNotReadyException:
        print(f"Trying to start Rekognition model {model_arn}")
        try:
            start_version_response = rekognition.start_project_version(
                ProjectVersionArn=model_arn,
                MinInferenceUnits=min_inference_units,
            )
            print(start_version_response)
        except Exception as e:
            raise ModelError(f"Model not ready and couldn't be started: {e}")

        # There is a get_waiter("project_version_running") available in the Rekognition Boto3 SDK, but it
        # requires the project ARN which at the time of writing can't be easily derived from the version ARN
        # (because it contains a different, project-related timestamp).
        #
        # Anyway we only provide this convenience to auto-start the version on first invokation to simplify
        # setup because Rek CL console doesn't currently have a UI option to start versions... So to keep our
        # Lambda config DRY and this code simple, we'll just return an error here telling the user to try
        # again when the model is ready.
        raise ModelError(f"Rekognition model now deploying... Please try again shortly")
    except rekognition.exceptions.InvalidS3ObjectException:
        raise MalformedRequest(
            f"Invalid S3 object location 's3://{bucket}/{photo}', please check your request'"
        )
    except rekognition.exceptions.ImageTooLargeException:
        raise MalformedRequest("Image too large to process with Rekognition Custom Labels")
    except rekognition.exceptions.InvalidImageFormatException:
        raise MalformedRequest("Invalid image format rejected by Rekognition Custom Labels")
    except ClientError as ce:
        # Other client errors (incl rate limiting, access problems, etc)
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
