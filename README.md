# End-to-End Smart OCR

[Amazon Textract's](https://aws.amazon.com/textract/) advanced extraction features go beyond simple OCR to recover structure from documents: Including tables, key-value pairs (like on forms), and other tricky use-cases like multi-column text.

**However, many practical applications need to combine this technology with use-case-specific logic** - such as:

- Pre-checking that submitted images are high-quality and of the expected document type
- Post-processing structured text results into business-process-level fields (e.g. in one domain "Amount", "Total Amount" and "Amount Payable" may be different raw annotations for the same thing; whereas in another the differences might be important!)
- Human review and re-training flows

This solution demonstrates how Textract can be integrated with:

- **Image pre-processing logic** - using [Amazon Rekognition Custom Labels](https://aws.amazon.com/rekognition/custom-labels-features/) to create a high-quality custom computer vision with no ML expertise required
- **Results post-processing logic** - using custom logic as well as NLP from [Amazon Comprehend](https://aws.amazon.com/comprehend/)
- **Human review and data annotation** - using [Amazon A2I](https://aws.amazon.com/augmented-ai/) and [Amazon SageMaker Ground Truth](https://aws.amazon.com/sagemaker/groundtruth/)

The design is modular, to show how this pre- and post-processing can be easily customized for different use-cases.


## Solution Architecture 

![Smart OCR Architecture Diagram](images/architecture-overview.png "Smart OCR Demo Architecture")

The solution has four high-level modules:

- [Preprocessing part to identify this image as "good" or "bad](1.img-pre-processing)
- [Textract for OCR](2.ocr-post-processing)
- [Human-In-The-Loop (A2I) for human intervention in case of bad images](3.a2i-review)
- [Web UI component to upload the receipt/document to S3 & view OCR result](4.web-gui)

Additional details on how to deploy these modules have been provided in the readme file in the respective folders.


## Getting Started

**WORK IN PROGRESS one-click deploy button (probably broken!)**

[![One-click deployment](https://oneclick.amplifyapp.com/button.svg)](https://console.aws.amazon.com/amplify/home#/deploy?repo=https://github.com/athewsey/textract-demo)


## AWS Services Used

**Machine Learning Services:**

- [Amazon SageMaker Ground Truth](https://aws.amazon.com/sagemaker/groundtruth/) - Manual labelling of training data set
- [Amazon Rekognition Custom Labels](https://aws.amazon.com/rekognition/custom-labels-features/) - Quickly build custom ML models to detect objects and classify image quality
- [Amazon Textract](https://aws.amazon.com/textract/) - Document text detection and analysis
- [Amazon Comprehend](https://aws.amazon.com/comprehend/) - Natural language processing (NLP) to extract insights about content of documents
- [Amazon Augmented AI (A2I)](https://aws.amazon.com/augmented-ai/) - Human intervention for low-confidence ML predictions

**Integration and Orchestration:**

- [AWS Lambda](https://aws.amazon.com/lambda/) - AWS Serverless components to execute code without worrying about servers
- [AWS API Gateway](https://aws.amazon.com/api-gateway/) - AWS API Management service
- [AWS Amplify](https://aws.amazon.com/amplify/) - Framework to build full-stack iOS, Android, Web, and React Native apps
- [AWS IoT Events](https://aws.amazon.com/iot-events/) - Secure, bi-directional communication between client and AWS Cloud
- [Amazon DynamoDB](https://aws.amazon.com/dynamodb/) - Highly scalable NoSQL database to store OCR labels
- [Amazon S3](https://aws.amazon.com/s3/) - Object store for documents and images
- [Amazon Cognito](https://aws.amazon.com/cognito/) - Handles user registration, authentication and authorization for the web app
