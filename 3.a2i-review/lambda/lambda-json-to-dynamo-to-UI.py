import json
import boto3
import os
import sys

# Define clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
iot = boto3.client('iot-data')


def lambda_handler(event, context):
    '''
    Triggered when a .json file is stored in 
    S3 "textract-ocr-unicorn-gym-asean-demo"
    under the directory "a2i-results"
    This lambda function loads the .json file, parses it, and stores 3 fields
    in DynamoDB
    '''
    
    # print(event)  # for testing

    for record in event['Records']:
        

        # getting important info from the event handler
        timestamp = record['eventTime']
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        print('Timestamp:', timestamp)
        print('Bucket:', bucket)
        print('Filename:', key)
        
        
        # load JSON object
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body']
        jsonObject = json.loads(content.read())
        #print('JSON content:', jsonObject)
        #print('Answers:', jsonObject['humanAnswers'])
        #print('Content:', jsonObject['humanAnswers'][0]['answerContent'])
        
        
        # parsing JSON object
        date = None
        vendor = None
        total = None
        
        if 'humanAnswers' in jsonObject:
            try:
                date = jsonObject['humanAnswers'][0]['answerContent']['date']
                vendor = jsonObject['humanAnswers'][0]['answerContent']['vendor']
                total = jsonObject['humanAnswers'][0]['answerContent']['total']
                worker_id = jsonObject['humanAnswers'][0]['workerId']
                taskObject = jsonObject['inputContent']['taskObject']
            except:
                print('Oops! Cannot find required JSON fields!')
            
        print('Date:',date)
        print('Vendor:',vendor)
        print('Total:',total)
        print('JSON taskObject:',taskObject)
        
      
    # comment out to get the actual taskObject
    # taskObject = os.environ['taskObject']  # only for testing
    
    # parsing taskObject
    bucketkey = taskObject
    print('Parsed bucketkey=',bucketkey)
    bucket_original = taskObject.rsplit('/',4)[1]
    print('Parsed bucket=',bucket_original)
    region_userid = taskObject.rsplit('/',4)[3]
    userid = region_userid.rsplit(':',2)[1]
    print('Parsed userid=',userid)
    iot_key = 'private/' + region_userid + '/' + taskObject.rsplit('/',4)[4]
    print('Parsed iot_key=',iot_key)
    
    
    # storing to DynamoDB
    table = dynamodb.Table('image-tracking')
    dynamoresponse = table.put_item(
        Item={
            "id" : userid,
            "bucketkey" : bucketkey,
            "bucket" : bucket_original,
            "key" : iot_key,
            "status" : "Completed",
            "result":{
                "vendor": vendor,
                "date": date, 
                "total": total
            }
        }
        )
             
    
    #publish to UI
    topic = iot_key.rsplit('/', 1)[0]
    #topic += '_test'  # only for testing (comment out for production)
    iotmessage={
        "id" : userid,
        "bucketkey" : bucketkey,
        "bucket" : bucket_original,
        "key" : iot_key,
        "status" : "Completed",
        "result":{
            "vendor": vendor,
            "date": date, 
            "total": total
        }
    }
    iotpayload=json.dumps(iotmessage)
    response_iot=iot.publish(topic=topic, qos=1, payload=iotpayload)
    
    print('Topic:', topic)
    print('Payload:', iotpayload)
    print('ResponseIOT', response_iot)
    

    return {
        'statusCode': 200,
        'body': json.dumps('Success')
    }
