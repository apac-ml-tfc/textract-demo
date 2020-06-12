# Smart OCR : Image Pre-Processing
## HOW TO: Using Amazon SageMaker Ground Truth and Amazon Rekognition Custom Labels

#Preprocessing flow
<br>![alt text ](https://github.com/apac-ml-tfc/textract-demo/blob/master/1.img-pre-processing/img-preprocessing-flow.png "Service Flow") 

Step to follow for Image Pre-Processing
 1. Prepare the training data set
 2. Create a Ground Truth Labelling Job and manually classify the image
 3. Link Ground Truth data set to Amazon Rekognition Custom Labels
 4. Create the ML Model on Amazon Rekognition Custom Labels by using Ground Truth data set

---
### Amazon SageMaker Ground Truth Labelling Job
Pre-requisites: Load the Training Image data set to the S3 bucket.
1. Go to the AWS console Amazon SageMaker-->GroundTruth
2. Naviagte to the Labeling Workforces menu. Create a "Private" labelling workforce.  private team with the team members email id. This shall sent an invitation email. Accept the email invitation
3. Navigate to the Labeling jobs and create a new labelling Job.
4. Login to the Portal
5. Manually classify individual images as "good/bad"
6. Once the labelling is completed, it shall generate a output manifest in the location s3://$BUCKET_NAME/$JOB_NAME/manifests/output.manifest
7. Once the output.manifest file is generated that completes the first process step of "manual labelling" of images using groundtruth

### Amazon Rekognition Custom Labels
1. Navigate to Services-->Amazon Rekognition Custom Labels menu
2. Create a Datasets[Refer screenshots]
3. Create a Project and Train the model
4. Once the model is trained you could view the results from "View Test Results"
5. Use the API Code to test the model from the AWS CLI


### Pre-requisites for AWS Lambda python code
- Lambda python runtime is version 3.7
- Lambda function handler is `lambda_function.lambda_handler`
- Define both `REKOGNITION_MODEL_ARN` and `LAMBDA_ENHANCED_IMAGE_ARN` environment variables on Image Pre-Processing Lambda function
