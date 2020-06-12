Instructions for setting up the lambda function: a2i-json-to-dynamo.py
-------------------------------------------------------------------------------

Objective:
----------
To get information from a .json file stored on a particular location in S3, 
update a DynamoDB table ('image-tracking') and then send an IoT notification to 
the UI. 


Trigger:
--------
(putting a .json file in the S3 bucket)
"textract-ocr-unicorn-gym-asean-demo" under the directory "a2i-results/"
        Event type: ObjectCreated
        Notification name: 86d37fce-12e5-4e96-ae2f-2234ea380d71
        Prefix: a2i-results/
        Suffix: .json


Permissions:
------------

1. AWSIoTDataAccess (for publishing results back to the UI)
        Allow: iot:Connect
        Allow: iot:Publish
        Allow: iot:Subscribe
        Allow: iot:Receive
        Allow: iot:GetThingShadow
        Allow: iot:UpdateThingShadow
        Allow: iot:DeleteThingShadow
        
2. S3 read only (for triggering the lambda function after an S3 .json put).
        Allow: s3:GetObject
        
3. DynamoDB read/write (for reading/writing to DynamoDB)
        Allow: dynamodb:DeleteItem
        Allow: dynamodb:GetItem
        Allow: dynamodb:PutItem
        Allow: dynamodb:Scan
        Allow: dynamodb:UpdateItem



Setting up the lambda function:
------------------------------

1. Initiate a new lambda function with the name "a2i-json-to-dynamo"
2. Copy the code from the a2i-json-to-dynamo.py to the code section of your new
   lambda function. 
3. Setup the permissions of the lambda function. Add the 3 permissions that 
   mentioned above. 
4. Setup the triggering mechanism that will initiate the lambda.