# Smart OCR : OCR Post-Processing
## HOW TO: Using AWS Lambda, Amazon Textract, Amazon Comprehend to extract business attributes from bill/voice

# OCR and A2I flow
<br>![alt text ](https://github.com/apac-ml-tfc/textract-demo/blob/master/2.ocr-post-processing/ocr-processing-and-a2i.png "Module flow")  

### Pre-requisites for AWS Lambda python code
- Lambda python runtime is version 3.8
- Lambda function handler is `lambda_function.lambda_handler`

- You can define Lambda environment variables as following:
    1. <strong>flowDefinitionArn</strong> is refering to Human loop loop in A2i
    2. <strong>avg_confthreshold</strong> is average ocr post processing threshold that you can define.
    3. <strong>preprocessingFunction</strong> is Preprocessing function to identifiying whether image quality is good, or bad.
    4. You may need follow IAM policy in order for OCR post processing function Execution role to work:
        - AWSLambdaFullAccess, AmazonS3FullAccess, CloudWatchFullAccess, AmazonDynamoDBFullAccess, AmazonTextractFullAccess, ComprehendFullAccess, AWSIoTFullAccess, AmazonAugmentedAllHumanLoopFullAccess
    <h4> *** In Production, We are highly recommended to apply least privilege principal for IAM role</h4>
---
## Step to follow to deploy OCR Post-Processing
 
 ## 1.) Dynamo DB 
 In this step, we will navigate to DynamoDB Console and create the DynamoDB used throughout this application

Login to AWS Console: https://console.aws.amazon.com/dynamodb/home?region=us-east-1#

* Click - **Create Table**
    * Bucket Name : **imnage-tracking**
    * Click checkbox **Add sort key** (bottom Partition Key Textbox)
        * Partition Key: **id**
        * Sort key: **bucketkey**
    * Leave all option as Default
* Click **Create**

#

## 2.) Create Lambda Function
 In this step, we will navigate to AWS Lambda Console and create the Labmda function used throughout this application

 Login to AWS Console: https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions


* 2.1) Create Lambda function by Click - **Create function**
    * Choose : **Author from scratch**
    * Function Name: **Your function name** (Ex. MyOCRProcessing)
    * Runtime: **Python 3.8** 
* Click: **Create function**


* 2.2) Create Lambda Code, In Lambda Function Code IDE 
    * 2.2.1) Create Textract parser
        * Click file : **New file named: trp.py**
        * Copy Code from **src/trp.py** to the **new file** that you have created, file name must be the same
        * Save Lambda function by **CTRL+S**
    * 2.2.2) Create Main OCR Function
        * Copy Code from **src/ocrpostprocess.py** to the **lambda_function.py** that you have created.  
        * Save Lambda function by **CTRL+S**  
# 
## 3.) Lambda Permession
In your Lambda function, You click **Permission**, and Click a **Your Lambda Execute Role name**, It will direct to your IAM role

* Click : **Attach Policies**
* You may need follow IAM policy in order for OCR post processing function Execution role to work: **AWSLambdaFullAccess, AmazonS3FullAccess, CloudWatchFullAccess, AmazonDynamoDBFullAccess, AmazonTextractFullAccess, ComprehendFullAccess, AWSIoTFullAccess, AmazonAugmentedAllHumanLoopFullAccess**
* Click : **Attach Policy**
#
Congraturation, You have finished OCR Post processing setup !!! 

