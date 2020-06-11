# Smart OCR : Image Pre-Processing
## HOW TO: Using Amazon SageMaker Ground Truth and Amazon Rekognition Custom Labels

Step to follow for Image Pre-Processing
 1. Prepare the training data set
 2. Create a Ground Truth Labelling Job and manually classify the image
 3. Link Ground Truth data set to Amazon Rekognition Custom Labels 
 4. Create the ML Model on Amazon Rekognition Custom Labels by using Ground Truth data set

---
### Amazon SageMaker Ground Truth Labelling Job


### Amazon Rekognition Custom Labels


### Pre-requisites for AWS Lambda python code
- Lambda python runtime is version 3.7
- Lambda function handler is `lambda_function.lambda_handler`
- Define both `REKOGNITION_MODEL_ARN` and `LAMBDA_ENHANCED_IMAGE_ARN` environment variables on Image Pre-Processing Lambda function