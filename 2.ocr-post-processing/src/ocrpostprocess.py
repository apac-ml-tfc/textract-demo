import boto3
import botocore
import datetime
import json
import time
import os
import uuid
import pprint
import urllib
from trp import Document

# Define clients
s3 = boto3.client('s3')
textract = boto3.client('textract')
comprehend = boto3.client(service_name='comprehend')
lambda_client = boto3.client('lambda')
iot= boto3.client('iot-data')

# Define acceptable average thresholds for OCR post processing
avg_confthreshold = os.environ["avg_confthreshold"]
avg_confthreshold = float(avg_confthreshold)


def lambda_handler(event, context):
# Extract payload event
    BUCKET = event['Records'][0]['s3']['bucket']['name']
    #documentName = event['Records'][0]['s3']['object']['key']
    documentName = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    cognitoid = documentName.rsplit('/', 1)[0]
    print('cognitoid:', cognitoid, 'bucket:', BUCKET, 'key:', documentName)
    
    # use the cognitoid as topic in your actual code
    topic = cognitoid 
    #topic = 'private/us-east-1:073c31fb-efea-434d-ac4c-caccbce7d42a'
  
    payload_img={
        "queryStringParameters":{
            "bucket": BUCKET,
            "image": documentName
            }
            }
 
    rekconition_response = lambda_client.invoke(
        FunctionName=os.environ['preprocessingFunction'],
        Payload=json.dumps(payload_img)
        )
    rekdata = rekconition_response['Payload'].read().decode() 
    rekresult = json.loads(rekdata)
    print(rekresult)
    
    print("Is Image good from preprocessing task?: {}".format(rekresult["body"].find("good") > 0))
    
    if rekresult["statusCode"] == 200 and rekresult["body"].find("good") > 0:
    # Call Amazon Textract via S3
        response = textract.analyze_document(
            Document={
                'S3Object': {
                'Bucket': BUCKET,
                'Name': documentName
            }
        },
        FeatureTypes=["FORMS","TABLES"])

        doc = Document(response)
    
        # Define post processing variables
        keyarrays = ["total","amount"]
        keyarraysdate = ["date"]
        text = ""
        vendor_name = ""
        date_print = ""
        badcount=0
        
        # Post processing Output
        vendor_name = ""
        vendor_confidence = 0
        array_total = []
        array_date = []
        date_confidence = 0
        inputContent = ""
        
        ###### Find the Vendor name, We fix with first line ######
        for item in response["Blocks"]:
            if item["BlockType"] == "LINE":
                if vendor_name == "":
                    vendor_name = item["Text"]
                    vendor_confidence = item["Confidence"]
                else:
                    text += item['Text']+" "
                       
        for page in doc.pages:  
            ###### Find Total Amount Key ######
            for key in keyarrays:
                fields = page.form.searchFieldsByKey(key)
                for field in fields:
                    # Find Total & Amount logic
                    if (field.key.text.lower().find("total") >= 0 or field.key.text.lower().find("amount") >= 0) and field.value is not None:
                        array_total.append([field.value.text,field.key.confidence])
                        
                        
            ###### Find Date Key ######
            for key in keyarraysdate:
                fields = page.form.searchFieldsByKey(key)
                for field in fields:
                    # Find Date logic
                    if field.key.text.lower().find("date") >= 0:
                        array_date = [field.value.text,field.key.confidence]
        
        
        ###### Print out Billing Attributed information post processing ######                
        #print("Vendor name: {} with Confidence {}".format(vendor_name,vendor_confidence))
        if (array_total):
            array_total = sorted(array_total, key=lambda x: x[0],reverse=True)
        else:
           badfile = documentName
           badcount+=1
 
        if (array_date and badcount != 1):
            badcount=0
            #print("Billing date: {} with Confidence {}".format(array_date[0],array_date[1]))
        elif(badcount != 1):
           badfile = documentName
           detect_entity = comprehend.detect_entities(Text=text, LanguageCode='en')
           EntityList=detect_entity.get("Entities")
           for s in EntityList:
            if s.get("Type")=="DATE":
                if s.get("Text").find("/") >= 0 or s.get("Text").find(":") >= 0 or s.get("Text").find("-") >= 0:
                    date_print+= s.get("Text").strip('\t\n\r')+ " "
                    date_confidence+=s.get("Score")
        else:
            badcount+=1
        
        if (date_print != ""):
            if date_confidence > 1:
                date_confidence = (date_confidence/2)*100
            else: 
                date_confidence = date_confidence*100
            array_date = [date_print,date_confidence]
        
        
        s3_fname = "s3://" + BUCKET+ "/" + documentName
        
        
        
        ########## Build Payload condition, Code is not yet optimized #########
        if (badcount > 1):
            print("Bad input receipt quality: s3:/{}/{} !".format(BUCKET,documentName))
            inputContent = {
                "taskObject": s3_fname,
                "date": "Need human review",
                "vendor": vendor_name,
                "total" : "Need human review the total"
                }
            print(inputContent)
            
            iotmessage={
                "id" : os.environ['userid'] ,
                "bucket" : BUCKET ,
                "key" : documentName,
                "status" : "Pending human review",
                "result":{
                    "vendor": vendor_name,
                    "date": "Need human review the date" , 
                    "total": "Need human review the total"
                }
            }
            iotpayload=json.dumps(iotmessage)
            response_iot=iot.publish(topic=topic, qos=1, payload=iotpayload)
            
            
            uniqueId = str(uuid.uuid4())
            human_loop_unique_id = uniqueId + '1'
            flowDefinitionArn = os.environ["flowDefinitionArn"]
            a2i_runtime_client = boto3.client('sagemaker-a2i-runtime')
            a2i_response = a2i_runtime_client.start_human_loop(
                HumanLoopName=human_loop_unique_id,
                FlowDefinitionArn=flowDefinitionArn,
                HumanLoopInput={
                    'InputContent': json.dumps(inputContent)
                    },
                    DataAttributes={
                        'ContentClassifiers': [
                            'FreeOfPersonallyIdentifiableInformation'
                            ]
                    }
                )
            print("Calling human loop ARN {}".format(flowDefinitionArn))
            
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table('image-tracking')
            dynamoresponse  = table.put_item(
                Item={
                    "id" : os.environ['userid'] ,
                    "bucketkey" : s3_fname,
                    "bucket" : BUCKET ,
                    "key" : documentName,
                    "status" : "Pending human review",
                    "result":{
                        "vendor": vendor_name,
                        "date": "Need human review the date" , 
                        "total": "Need human review the total"
                    }
                }
                )
        else:
            avg_confidence = (vendor_confidence+array_total[0][1]+array_date[1])/3
            print("Average confidence percent after OCR Processing: {}".format(avg_confidence))
            if avg_confidence < avg_confthreshold:
                a2i_runtime_client = boto3.client('sagemaker-a2i-runtime')
                inputContent = {
                    "taskObject": s3_fname,
                    "date": array_date[0],
                    "vendor": vendor_name,
                    "total" : array_total[0][0]
                }
                print(inputContent)
                
                
                iotmessage={
                "id" : os.environ['userid'] ,
                "bucket" : BUCKET ,
                "key" : documentName,
                "status" : "Pending human review",
                "result":{
                    "vendor": vendor_name,
                    "date": "Need human review the date" , 
                    "total": "Need human review the total"
                    }
                }
                iotpayload=json.dumps(iotmessage)
                response_iot=iot.publish(topic=topic, qos=1, payload=iotpayload)
                
                
                uniqueId = str(uuid.uuid4())
                human_loop_unique_id = uniqueId + '1'
                flowDefinitionArn = os.environ["flowDefinitionArn"]
                a2i_response = a2i_runtime_client.start_human_loop(
                    HumanLoopName=human_loop_unique_id,
                    FlowDefinitionArn=flowDefinitionArn,
                    HumanLoopInput={
                        'InputContent': json.dumps(inputContent)
                    },
                    DataAttributes={
                        'ContentClassifiers': [
                            'FreeOfPersonallyIdentifiableInformation'
                            ]
                    }
                )
                print("Calling human loop ARN {}".format(flowDefinitionArn))
                
                dynamodb = boto3.resource('dynamodb')
                table = dynamodb.Table('image-tracking')
                dynamoresponse  = table.put_item(
                Item={
                    "id" : os.environ['userid'] ,
                    "bucketkey" : s3_fname,
                    "bucket" : BUCKET ,
                    "key" : documentName,
                    "status" : "Pending human review",
                    "result":{
                        "vendor": vendor_name,
                        "date": array_date[0],
                        "total": array_total[0][0]
                    }
                }
                )
            else:
                inputContent = {
                    "taskObject": s3_fname,
                    "date": array_date[0],
                    "vendor": vendor_name,
                    "total" : array_total[0][0]
                }
                
                
                iotmessage={
                "id" : os.environ['userid'] ,
                "bucket" : BUCKET ,
                "key" : documentName,
                "status" : "Completed",
                "result":{
                    "vendor": vendor_name,
                    "date": array_date[0] , 
                    "total": array_total[0][0]
                    }
                }
                iotpayload=json.dumps(iotmessage)
                response_iot=iot.publish(topic=topic, qos=1, payload=iotpayload)
                
                
                dynamodb = boto3.resource('dynamodb')
                table = dynamodb.Table('image-tracking')
                dynamoresponse  = table.put_item(
                Item={
                    "id" : os.environ['userid'],
                    "bucketkey" : s3_fname,
                    "bucket" : BUCKET ,
                    "key" : documentName,
                    "status" : "Completed",
                    "result":{
                        "vendor": vendor_name,
                        "date": array_date[0],
                        "total": array_total[0][0]
                    }
                }
                )
                print(inputContent)
    else:
        print("Image quality is low, please re-take your picture again...") 
        inputContent="Image quality is low, please re-take your picture again..."
    
    return {
     'full_payload' : json.dumps(inputContent)
    }

    

    
