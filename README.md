# End to End Smart OCR 

Enhancing OCR technology for real-life use cases.

 To build a Web Application that demonstrates the value of Amazon Textract augmented with A2I for manual overrides. Intelligent input validation of images using enhance pre-processing algorithms  
 <br>


 
# Solution Architecture 

<br>![alt text ](https://github.com/apac-ml-tfc/textract-demo/blob/master/smartocr-solution-architecture.png "Smart OCR Demo Architecture")




## This module has total four components
  - [Web UI component to upload the receipt/document to S3 & view OCR result](https://github.com/apac-ml-tfc/textract-demo/tree/master/4.web-gui)
  - [Preprocessing part to identify this image as "good" or "bad](https://github.com/apac-ml-tfc/textract-demo/blob/master/1.img-pre-processing/README.md)
  - [Textract for OCR](https://github.com/apac-ml-tfc/textract-demo/blob/master/2.ocr-post-processing/README.md)
  - [Human-In-The-Loop (A2I) for human intervention in case of bad images](https://github.com/apac-ml-tfc/textract-demo/blob/master/3.a2i-review/a2i_humanloop.ipynb)

  Additional details on how to deploy these modules have been provided in the readme file in the respective folders.

### AWS Services Used
* [AWS Groundtruth] - Manual labelling of training data set
* [AWS Rekognition Custom Labels] - quickly build custom ML models to detect objects and classify image quality
* [AWS Textract] - document text detection and analysis
* [Amazon Comprehend] - uses natural language processing (NLP) to extract insights about content of documents
* [Amazon Augmented AI (A2I)] - build the workflows required for human review of ML predictions
* [AWS Lambda] - AWS Serverless components to execute code without worrying about servers
* [AWS API Gateway] - AWS API Management service
* [AWS Amplify] - framework to build fullstack iOS, Android, Web, and React Native apps
* [AWS IoT Core] - enables secure, bi-directional communication between client and AWS Cloud over MQTT and HTTP
* [Amazon DynamoDB] - fully managed NoSQL database service to store ocr labels
* [Amazon S3] - object store for documents and images
* [Amazon Cognito] - handles user registration, authentication and authorization for the web app



