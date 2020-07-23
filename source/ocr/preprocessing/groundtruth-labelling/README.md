# Guideline for implement Amazon SageMaker Ground Truth

Steps for implementing Amazon SageMaker Ground Truth via AWS Management Console.

1. Create labeling job Amazon SageMaker Ground Truth.

![alt text](01_groundtruth_label_job_creation.png)

2. Create manifest file on S3 bucket.

![alt text](02_groundtruth_label_job_creation.png)

3. Select the manifest for this job.

![alt text](03_groundtruth_label_job_creation.png)

4. Create the job and provide IAM role. Please ensure that IAM role of the job can access selected S3 bucket.

![alt text](04_groundtruth_label_job_creation.png)

5. Choose "Image Classification (Single Label)" task.

![alt text](05_groundtruth_label_job_creation.png)

6. Select "Private" workforce type.

![alt text](06_groundtruth_label_job_creation.png)

7. Create the job and verify the job result.

![alt text](07_groundtruth_label_job_creation.png)

8. Login to the workforce job console.

![alt text](08_groundtruth_label_job_creation.png)

9. Choose the workforce job.

![alt text](09_groundtruth_label_job_creation.png)

10. Do manual label of the image based on classifiction condition. An example show binary label types, Good and Bad labels.

![alt text](10_groundtruth_label_job_creation.png)

11. Repeat the label job, until all of the image are labeled.

![alt text](11_groundtruth_label_job_creation.png)
