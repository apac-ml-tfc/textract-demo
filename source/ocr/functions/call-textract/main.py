"""Lambda to start Textract OCR (from Step Function)

TODO: Support async Textract job integration for multi-page document
TODO: Support alternative results delivery mechanisms e.g. DynamoDB?
"""

# Python Built-Ins:
import io
import json
import os

# External Dependencies:
import boto3

s3 = boto3.resource("s3")
textract = boto3.client("textract")

is_textract_sync = os.environ.get("TEXTRACT_INTEGRATION_TYPE", "ASYNC") in ("SYNC", "SYNCHRONOUS")


class MalformedRequest(ValueError):
    pass

# See commented-out draft snippet below
# class WaitingForJob(RuntimeError):
#     pass

def handler(event, context):
    try:
        srcbucket = event["Input"]["Bucket"]
        srckey = event["Input"]["Key"]
        output_type = event["Output"].get("Type", "s3")
        output_type_lower = output_type.lower()
        if output_type_lower == "inline":
            pass  # No other config to collect
        elif output_type_lower == "s3":
            destbucket = event["Output"].get("Bucket", srcbucket)
            if event["Output"].get("Key"):
                destkey = event["Output"]["Key"]
            else:
                prefix = event["Output"].get("Prefix", "")
                destkey = "".join([
                    (prefix + "/" if prefix else ""),
                    srckey,
                    ".textract.json",
                ])
        else:
            raise MalformedRequest(f"Unknown output integration type '{output_type}': Expected 'Inline' or 'S3'")
    except KeyError as ke:
        raise MalformedRequest(f"Missing field {ke}, please check your input payload")

    if is_textract_sync:
        result = textract.analyze_document(
            Document={
                'S3Object': {
                    'Bucket': srcbucket,
                    'Name': srckey,
                },
            },
            FeatureTypes=["FORMS", "TABLES"],
        )
    else:
        # TODO Implement async textract calls
        raise NotImplementedError("Async Textract integration not ready yet")
        # job = textract.start_document_analysis(
        #     DocumentLocation={
        #         'S3Object': {
        #             'Bucket': srcbucket,
        #             'Name': srckey,
        #         }
        #     },
        #     FeatureTypes=["FORMS", "TABLES"],
        #     # ClientRequestToken allows idempotency from token to job, which will let us use retries of this state to poll for success!
        #     # An alternative would be to use SNS and async Lambda integration
        #     ClientRequestToken=f"s3://{bucket}/{key}",
        #     #JobTag='string',
        #     # NotificationChannel={
        #     #     'SNSTopicArn': 'string',
        #     #     'RoleArn': 'string'
        #     # }
        # )
        # result = textract.get_document_analysis(
        #     JobId=job["JobId"],
        #     #NextToken= TODO: Paginate responses
        # )
        # if result["JobStatus"] == "IN_PROGRESS":
        #     raise WaitingForJob(job["JobId"])
        # elif result["JobStatus"] in ("SUCCEEDED", "PARTIAL_SUCCESS"):
        #     # TODO: These are the results DocumentMetadata, NextToken, Blocks, Warnings, AnalyzeDocumentModelVersion... Paginate!
        #     pass
        # else:
        #     raise ValueError("Textract job {} entered failure state '{}'{}".format(
        #         job["JobId"],
        #         job["JobStatus"],
        #         f" ({job.get('StatusMessage')})" if job.get("StatusMessage") else ""
        #     ))

    if output_type_lower == "inline":
        return result
    elif output_type_lower == "s3":
        resio = io.BytesIO(json.dumps(result).encode("utf-8"))
        s3.Bucket(destbucket).upload_fileobj(resio, destkey)
        return {
            "Bucket": destbucket,
            "Key": destkey,
            "S3Uri": f"s3://{destbucket}/{destkey}",
        }
    else:
        # Should have been caught by the initial event processing!
        raise MalformedRequest(f"Unknown output integration type '{output_type}': Expected 'Inline' or 'S3'")
