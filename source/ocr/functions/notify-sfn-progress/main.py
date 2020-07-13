"""Lambda function to publish Step Functions log events to IoT Core (and therefore the web UI)

Enable logging on your state machine, then trigger this Lambda via an AWS::Logs::SubscriptionFilter

For a complete list of AWS Step Functions history event `type`s, see:
https://docs.aws.amazon.com/step-functions/latest/apireference/API_HistoryEvent.html

We assume listening to events of types: Execution* and *State*

TODO: Uncomment the final IoT publishing step!

"""

# Python Built-Ins:
import base64
import gzip
import json
import os
import time
import traceback

# External Dependencies:
import boto3
from expiringdict import ExpiringDict

ddb = boto3.resource("dynamodb")
iot = boto3.client("iot-data")

topic_prefix = "private"

# The only resource ID we're guaranteed to get from Step Functions executions (e.g. if exiting with error) is
# the Step Functions Execution ID. Because in our architecture executions are triggered *by an S3 upload*,
# web clients *don't actually know* what executions they've kicked off - only what file they created. In
# addition, our IoT topic permissions are partitioned by *Cognito Identity ID*, so we'll need that to push
# execution progress notifications.
#
# Here we use a simple in-memory cache (because we're likely to get many events in quick succession if the
# Lambda is warm) in front of a DynamoDB table (in case the Lambda goes cold).
ownership_cache = ExpiringDict(max_len=200, max_age_seconds=60*60*24*7)
ownership_table = ddb.Table(os.environ["EXECUTION_OWNERSHIP_TABLE_NAME"])


def handler(event, context):
    print("EXTRACTING PAYLOADS")
    print(event)

    # CloudWatch delivers base64-encoded zipped data:
    zipdata = base64.b64decode(event["awslogs"]["data"])
    payload_bytes = gzip.decompress(zipdata)
    payload = json.loads(payload_bytes)

    print("PROCESSING LOGS")
    for log in payload["logEvents"]:
        print(f"Processing log: {log}")
        try:
            process_event(log)
        except Exception as e:
            traceback.print_exc()
            print("ERROR: Uncaught error in log event processing, moving to next event")
        

def process_event(log):
    timestamp = log["timestamp"]
    message = json.loads(log["message"])
    print(f"Log message: {message}")
    message_type = message["type"]  # e.g. TaskStateEntered
    execution_arn = message["execution_arn"]

    notification = {
        "executionArn": execution_arn,
        "timestamp": timestamp,
        "type": message_type,
    }

    state_name = message["details"].get("name") if "State" in message_type else None
    if state_name:
        notification["stateName"] = state_name

    # Establish the ownership of the Execution:
    cached_ownership = ownership_cache.get("execution_arn")
    if cached_ownership is None:
        # Does the event have sufficient details to interpret ownership?
        try:
            # TODO: Maybe more permissive scraping logic?
            sfn_input = json.loads(message["details"]["input"])
            identity_id = sfn_input \
                ["detail"]["userIdentity"]["sessionContext"] \
                ["webIdFederationData"]["attributes"]["cognito-identity.amazonaws.com:sub"]
            reqparams = sfn_input.get("detail", {}).get("requestParameters", {})
            preserved_input = sfn_input.get("Input", {})
            if "bucketName" in reqparams and "key" in reqparams:
                s3_uri = f"s3://{reqparams['bucketName']}/{reqparams['key']}"
            elif "Bucket" in preserved_input and "Key" in preserved_input:
                s3_uri = f"s3://{preserved_input['Bucket']}/{preserved_input['Key']}"
            else:
                raise ValueError("Object S3 URI not available on event")
            publish_to_ddb = True
        except (KeyError, ValueError) as e:
            # Nope - not in cache and event doesn't have enough information to trace.
            # Try a DDB lookup to add to cache, otherwise we're stuffed:
            ddb_fetch_response = ownership_table.get_item(Key={ "ExecutionId": execution_arn })
            if "Item" in ddb_fetch_response:
                identity_id = ddb_fetch_response["Item"]["IdentityId"]
                s3_uri = ddb_fetch_response["Item"]["S3Uri"]
                publish_to_ddb = False
            else:
                # FAIL - print error and move on to next message in queue
                print("".join([
                    "ERROR: Couldn't trace IdentityID and S3Uri from event payload or cache. ",
                    f"Unable to notify {notification}",
                ]))
                return

        ownership_cache[execution_arn] = {
            "IdentityId": identity_id,
            "S3Uri": s3_uri,
        }
        if publish_to_ddb:
            ownership_table.put_item(
                Item={
                    "ExecutionId": execution_arn,
                    "ExpiresAt": int(time.time() + 60*60*24*7),  # time.time is UTC epoch seconds
                    "IdentityId": identity_id, 
                    "S3Uri": s3_uri,
                }
            )
    else:
        identity_id = cached_ownership["IdentityId"]
        s3_uri = cached_ownership["S3Uri"]

    # Now that ownership is known, we can send our notification
    notification["s3Uri"] = s3_uri

    topic_name = f"{topic_prefix}/{identity_id}"
    print(f"Prepared notification for topic {topic_name}: {notification}")
    iot.publish(topic=topic_name, qos=1, payload=json.dumps(notification))
