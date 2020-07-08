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

# External Dependencies:
import boto3


iot = boto3.client("iot-data")


def handler(event, context):
    print("EXTRACTING PAYLOADS")
    print(event)

    # CloudWatch delivers base64-encoded zipped data:
    zipdata = base64.b64decode(event["awslogs"]["data"])
    payload_bytes = gzip.decompress(zipdata)
    payload = json.loads(payload_bytes)
    print(payload)

    print("PROCESSING LOGS")
    for log in payload["logEvents"]:
        print(f"Processing log: {log}")
        timestamp = log["timestamp"]
        message = json.loads(log["message"])
        message_type = message["type"]  # e.g. TaskStateEntered
        execution_arn = message["execution_arn"]

        state_name = message["details"].get("name") if "State" in message_type else None

        notification = {
            "executionArn": execution_arn,
            "timestamp": timestamp,
            "type": message_type,
        }

        if state_name:
            notification["stateName"] = state_name

        topic_name = None

        if "input" in message["details"]:
            sfn_input = json.loads(message["details"]["input"])

            # Try to get the raw image location from the location it appears in initial SFN triggered input:
            reqparams = sfn_input.get("detail", {}).get("requestParameters", {})
            # ...Or else from the location the first state stores it which is usually preserved:
            preserved_input = sfn_input.get("Input", {})
            if "bucketName" in reqparams and "key" in reqparams:
                topic_name = reqparams["bucketName"] + "/" + reqparams["key"]
            elif "Bucket" in preserved_input and "Key" in preserved_input:
                topic_name = preserved_input["Bucket"] + "/" + preserved_input["Key"]
            else:
                print("WARNING: Couldn't recover correct topic name - using execution ARN")
                topic_name = execution_arn
        else:
            print("WARNING: No input data recorded on event - using execution ARN")
            topic_name = execution_arn

        print(f"Prepared notification for topic {topic_name}: {notification}")

        # iot.publish(
        #     topic=, # TODO: How do we pick a topic_name that the client knows to listen to?
        #     qos=1,
        #     payload=json.dumps(notification)
        # )
