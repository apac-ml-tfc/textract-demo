# End to End Smart OCR 

Enhancing OCR technology for real-life use cases.

 To build a Web Application that demonstrates the value of Amazon Textract augmented with A2I for manual overrides. Intelligent input validation of images using enhance pre-processing algorithms  
 <br>


 
# Solution Architecture 
<br>




## This module has total four components
  - Web UI component to upload the receipt/document to S3
  - Preprocessing part to identify this image as "good" or "bad"
  - Textract for OCR
  - Human-In-The-Loop (A2I) for human intervention in case of bad images

  Additional details on how to deploy these modules have been provided in the readme file in the respective folders.

### AWS Services Used
* [AWS Groundtruth] - Manual labelling of training data set
* [AWS Rekognition CustomLabel] - ML For used for Image classification(good/bad)
* [AWS Textract & A2I] - AI developer service to analyse the document and extract text
* [AWS Lambda] - AWS Serverless components to execute code without worrying about servers
* [AWS API Gateway] - AWS API Management service
* [AWS Amplify]


