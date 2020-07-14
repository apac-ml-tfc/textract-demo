# Image Pre-Processing

Using [Amazon SageMaker Ground Truth](https://aws.amazon.com/sagemaker/groundtruth/) and [Amazon Rekognition Custom Labels](https://aws.amazon.com/rekognition/custom-labels-features/) to build an image classifier with no ML experience required!


## Component Architecture

The objective of the pre-processing flow is to classify the incoming image as "good" (acceptable for OCR) or "bad" (likely to yield error results) to detect and reject poor quality images earlier in the process.

Note that many practical solutions may also attempt **enhancing** the provided images to correct skew, blur, lighting problems or other common issues: For this reason, this component **returns an S3 URI** (rather than a 'yes/no' check) - to make it easier to extend.

<br>![alt text](img-preprocessing-flow.png "Service Flow") 


## Setup Steps

To set up this module after deploying the solution, you'll need to:

- **Label** some training data of good & bad images
- **Train** a Rekognition Custom Labels solution
- **Deploy** the model and connect it to the demo solution stack

### [1. Label the Data](groundtruth-labelling)

> **Note:** Since we're just doing a toy classification problem with a small dataset, it's possible to skip the SageMaker Ground Truth step and just organize your images into folders named "bad" and "good" in S3!
>
> ...But this is a good opportunity to see how SageMaker Ground Truth could help you with image annotation workflows and distributing annotation effort between teams.

Pre-requisites: Load the Training Image data set to the S3 bucket.
1. Go to the AWS console Amazon SageMaker-->GroundTruth
2. Naviagte to the Labeling Workforces menu. Create a "Private" labelling workforce.  private team with the team members email id. This shall sent an invitation email. Accept the email invitation
3. Navigate to the Labeling jobs and create a new labelling Job.
4. Login to the Portal
5. Manually classify individual images as "good/bad"
6. Once the labelling is completed, it shall generate a output manifest in the location s3://$BUCKET_NAME/$JOB_NAME/manifests/output.manifest
7. Once the output.manifest file is generated that completes the first process step of "manual labelling" of images using groundtruth

### [2. Train the Model](rekognition-ml-model)

1. Navigate to Services-->Amazon Rekognition Custom Labels menu
2. Create a Datasets[Refer screenshots]
3. Create a Project and Train the model
4. Once the model is trained you could view the results from "View Test Results"
5. Use the API Code to test the model from the AWS CLI


### [3. Deploy and Integrate]()

1. Copy your model ARN from the [Rekognition Custom Labels Console](https://console.aws.amazon.com/rekognition/custom-labels) as before
1. In the [AWS Lambda Console](https://console.aws.amazon.com/lambda/), find your deployed `FunctionPreProcess` function
1. In the Lambda function **Configuration** page, set the `REKOGNITION_MODEL_ARN` **environment variable** to your model ARN

Your workflow should now be connected and ready to use the model for incoming requests!
