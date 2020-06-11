# End to End Smart OCR 

Enhancing OCR technology for real-life use cases.

 To build a Web Application that demonstrates the value of Amazon Textract augmented with A2I for manual overrides. Intelligent input validation of images using enhance pre-processing algorithms
 
# Solution Architecture





# Workstreams
  - Preprocessing
  - Web User Interface + Textract OCR
  - Human-In-The-Loop (A2I)

### AWS Services Used
* [AWS Groundtruth] - Manual labelling of training data set
* [AWS Rekognition CustomLabel] - ML For used for Image classification(good/bad)
* [AWS Textract] - AI developer service to analyse the document and extract text
* [AWS Lambda] - AWS Serverless components to execute code without worrying about servers
* [AWS API Gateway] - AWS API Management service


### Steps to Deploy

### This sample uses a pre-trained model which has been trained with a sample dataset of receipts. If you need to update the model, you will have to enhance your environment by taking additional steps as below:
* Label your data - Upload your sample receipts to a S3 bucket and create a manifest file. Use AWS Groundtruth to label these images using private, public, AWS staff or your team.
* Create a new Rekognition Custom Labels Model using a new Project under Rekogntion - Custom Labels. Follow the guidance provided by widget



### Todo

 - Automation of the various artifacts
