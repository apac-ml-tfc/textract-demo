# Guideline for implement Amazon Rekognition Custom Labels

Steps for implement Amazon Rekognition Custom Labels with Ground Truth Data Set

1. Create dataset on Amazon Rekognition Custom Labels by selecting "Image images labeled by Amazon SageMaker Ground Truth". Also provide the manifest file of Grouth Truth location.

![alt text](01_rekognition_ml_model_data_set_creation.png)

2. Configure S3 bucket policy to allow access from Amazon Rekognition Custom Labels.

![alt text](02_rekognition_ml_model_data_set_creation.png)

3. Verify the dataset that you created.

![alt text](03_rekognition_ml_model_data_set_creation.png)

4. Create Rekognition Custom Labels model by selecting Grouth Truth dataset.

![alt text](04_rekognition_ml_model_data_set_creation.png)
