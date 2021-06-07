# Human Review with Amazon A2I

## Component Architecture

This notebook is triggered by a lambda function which has done postprocess works after Textract API. For A2I work directly within your API calls to Textract's Analyze Document API, refer to [this official sample notebook](https://github.com/aws-samples/amazon-a2i-sample-jupyter-notebooks/blob/master/Amazon%20Augmented%20AI%20(A2I)%20and%20Textract%20AnalyzeDocument.ipynb)

## Setting Up

After the solution stack has deployed, you'll still need to set up the following:

- Create a private team in Amazon SageMaker Ground Truth, setting yourself up with credentials as a reviewer (or re-use your existing team if you created one already for the [preprocessing module](../preprocessing))
- Upload the provided [worker task template](a2i-text-with-checkboxes.liquid.html) as a custom task template in Amazon A2I
- Create an A2I Human Review Workflow linking the template and your review 'team'
- In the [AWS SSM Parameter Store](https://console.aws.amazon.com/systems-manager/parameters/?&tab=Table) console, find the deployed stack's `DefaultHumanFlowArn` parameter.
- **Edit** your parameter to set the *Value* as the ARN of your A2I workflow.

We provide a detailed walkthrough of these steps in [a2i_humanloop.ipynb](a2i_humanloop.ipynb).
<!-- TODO: Update the notebook with the new SSM-based walkthrough -->

> **Note**: For more than 70 official custom task UIs, check out https://github.com/aws-samples/amazon-a2i-sample-task-uis

## Running the Demo

To run the demo, follow the steps below

1) Join the humanflow-team private team
2) Upload the receipt to the web ui and make sure it triggers the human review
3) Login to the private team labelling console https://g27hwd6auf.labeling.us-east-1.sagemaker.aws
4) There will be a task named "human flow task"
5) Open the task and review/amend the textract outputs and complete the task
