# Getting Started with A2I

## 1. Set up A2I



Go through the steps in the notebook a2i_humanloop.ipynb 

+ this notebook is triggered by a lambda function which has done postprocess works after Textract API. For A2I work directly within your API calls to Textract's Analyze Document API, you may refer to [notebook here](https://github.com/aws-samples/amazon-a2i-sample-jupyter-notebooks/blob/master/Amazon%20Augmented%20AI%20(A2I)%20and%20Textract%20AnalyzeDocument.ipynb)
+ to create a task ui, you need to define a ui template to work with. For other pre-built UIs (70+), check: https://github.com/aws-samples/amazon-a2i-sample-task-uis




## 2. Preparing CDK in Cloud9

Please bring up a Cloud9 instance by going to https://ap-southeast-1.console.aws.amazon.com/cloud9/home/product. Cloud9 will provide you terminal access to run AWS CLI.

First create the AWS CDK Toolkit. The toolkit is a command-line utility which allows you to work with CDK apps.

```
npm install -g aws-cdk@1.44.0

```

In the terminal of the Cloud9, run the following command to create an empty directory.

```
mkdir cdklambda && cd cdklambda

```

We will use cdk init to create a new TypeScript CDK project:

```
cdk init sample-app --language typescript

```

Open a new terminal session (or tab). You will keep this window open in the background for the duration of the workshop.

From your project directory run:

```
cd cdklambda

```

And:

```
npm run watch

```

This will start the TypeScript compiler (tsc) in “watch” mode, which will monitor your project directory and will automatically compile any changes to your .ts files to .js.

## 3. Create the Human Post Processing lambda

Open up lib/cdklambda-stack.ts. This is where the meat of our application is.

cdklambda-stack.ts looks like this

```ts
import * as cdk from '@aws-cdk/core';
import * as iam from '@aws-cdk/aws-iam';
import * as lambda from '@aws-cdk/aws-lambda';
import * as path from 'path';

export class CdklambdaStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    //Create the IAM role
    const taskrole = new iam.Role(this, 'S3-readonly-DynamoDB', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com')
    });
    
    taskrole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSIoTDataAccess'));
    taskrole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonS3ReadOnlyAccess'));
    taskrole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonDynamoDBFullAccess'));
    taskrole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/CloudWatchFullAccess'));
    
     //Create the Lambda
     const fn = new lambda.Function(this, 'a2i-json-to-dynamo-cdk', {
        runtime: lambda.Runtime.PYTHON_3_6,
        handler: 'lambda_function.lambda_handler',  // file is "lambda_function", function is "lambda_handler"
        code: lambda.Code.fromAsset(path.join(__dirname, 'lambda')), // code loaded from "lambda" directory
      });
      
      fn.addEnvironment('avg_confthreshold','60');
      fn.addEnvironment('flowDefinitionArn','arn:aws:sagemaker:us-east-1:077546553367:flow-definition/yuan-textract-demo-cd65cc50-2630-40b6-8664-e6f13e029f29');
      fn.addEnvironment('preprocessingFunction',' arn:aws:lambda:us-east-1:077546553367:function:PreProcessImage:$LATEST');
      fn.addEnvironment('userid','us-east-1:073c31fb-efea-434d-ac4c-caccbce7d42a');

    
    
  }
}

```

Let’s deploy:

```
cdk deploy

```

You’ll notice that cdk deploy deployed your CloudFormation stack and create the lambda



## 4. Create the s3 trigger to invoke the lambda

S3 bucket will trigger the "a2i-json-to-dynamo" lambda whenever there is a new output.json in folder s3://textract-ocr-unicorn-gym-asean-demo/a2i-results

To configure S3 notification we use following command:

```
aws s3api put-bucket-notification-configuration --bucket textract-ocr-unicorn-gym-asean-demo --notification-configuration file://notification.json

```

Notification.json describes how the trigger should look like, for example:

```
Notification.json describes how the trigger should look like, for example:

{
"LambdaFunctionConfigurations": [
    {
      "Id": "my-lambda-function-s3-event-configuration",
      "LambdaFunctionArn": "arn-of-aws-lambda-function",
      "Events": [ "s3:ObjectCreated:Put" ],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "a2i-results/"
            },
            {
              "Name": "suffix",
              "Value": ".json"
            }
          ]
        }
      }
    }
  ]
}

```


## 5. Running the demo

To run the demo, follow the steps below

1) Join the humanflow-team private team
2) Upload the receipt to the web ui and make sure it triggers the human review
3) Login to the private team labelling console https://g27hwd6auf.labeling.us-east-1.sagemaker.aws
4) There will be a task named "human flow task"
5) Open the task and review/amend the textract outputs and complete the task