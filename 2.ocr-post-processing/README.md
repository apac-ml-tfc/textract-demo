# Smart OCR : OCR Post-Processing
## HOW TO: Using AWS Lambda, Amazon Textract, Amazon Comprehend to extract business attributes from bill/voice

### Pre-requisites for AWS Lambda python code
- Lambda python runtime is version 3.8
- Lambda function handler is `lambda_function.lambda_handler`
- You can define Lambda environment variables as following:
    1. flowDefinitionArn is refering to Human loop loop in A2i
    2. avg_confthreshold is average ocr post processing threshold that you can define.
    3. preprocessingFunction is Preprocessing function to identifiying whether image quality is good, or bad.
    4. For the completed demo purposed ocr post processing function Execution role should include:
        - AWSLambdaFullAccess, AmazonS3FullAccess, CloudWatchFullAccess, AmazonDynamoDBFullAccess, AmazonTextractFullAccess, ComprehendFullAccess, AWSIoTFullAccess, AmazonAugmentedAllHumanLoopFullAccess

        ** It's not recommended for production usage, You can use IAM access analyzer to check.
---
### Step to follow to deploy Image Post-Processing
 1. Create lambda function 
 2. Deploy file trp.py
 3. Deploy file ocrpostprocess.py
 ---

