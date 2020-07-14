"""Lambda function to resume a Step Functions flow on completion of an A2I human loop

How to use:
- Use a lambda:invoke.waitForTaskToken task Lambda to start your human loop
- Add a `taskToken` field to your task input when starting the loop, containing your SFn token
- Use an S3 subscription to trigger this Lambda when objects are created in your A2I output bucket

This function hard-codes the expected structure of the task (receipt capture) to simplify results for output
back to Step Functions - so you'll need to modify it if changing task.
"""

# Python Built-Ins:
import json
import os
import sys

# External Dependencies:
import boto3

s3 = boto3.resource("s3")
sfn = boto3.client("stepfunctions")


class ReviewFailed(ValueError):
    """Returned to SFN when review cycle completed unhealthily (e.g. with no human responses)"""
    pass

class MalformedReviewResponse(ValueError):
    """Returned to SFN when review cycle completed with bad output format (e.g. incompatible workflow?)"""
    pass


def handler(event, context):
    """S3 bucket subscription Lambda to pick up and continue processing flow for A2I review results

    Triggered by uploads to the S3 human reviews bucket (see subscriptions / CloudFormation for details)

    Input events should be formatted as per S3 notifications - described here:
    https://docs.aws.amazon.com/lambda/latest/dg/with-s3.html
    """
    # Notifications come through in batches
    for record in event["Records"]:
        timestamp = record["eventTime"]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        if key.endswith(".json"):
            print(f"Processing {timestamp} | s3://{bucket}/{key}")
        else:
            print(f"Skipping (not .json) {timestamp} | s3://{bucket}/{key}")
            continue

        # Need to load the result file to extract the Step Functions task token:
        result_response = s3.Object(bucket, key).get()
        result = json.loads(result_response["Body"].read())

        task_token = result["inputContent"].get("taskToken")
        if not task_token:
            print(f"WARNING: Missing task token, ignoring result")
            continue
        try:
            if not len(result.get("humanAnswers", [])):
                raise ReviewFailed("A2I review finished with no human responses")

            # We'll assume you're only using 1-fold review in this example:
            human_answer = result["humanAnswers"][0]
            date = human_answer["answerContent"]["date"]
            total = human_answer["answerContent"]["total"]
            vendor = human_answer["answerContent"]["vendor"]
            worker_id = human_answer["workerId"]

            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps({
                    "Date": date,
                    "Total": total,
                    "Vendor": vendor,
                    "WorkerId": worker_id,
                }),
            )
            print("Notified task complete")
        except KeyError as ke:
            sfn.send_task_failure(
                taskToken=task_token,
                error="MalformedReviewResponse",
                cause=f"Missing field: {str(ke)}",
            )
            print("Notified task failed")
        except Exception as e:
            # Like the default direct-to-Lambda integration, we'll return the Python exception type name
            # and the message:
            sfn.send_task_failure(
                taskToken=task_token,
                error=type(e).__name__,
                cause=str(e),
            )
            print("Notified task failed")

    return {
        "statusCode": 200,
        "body": json.dumps("Success"),
    }
