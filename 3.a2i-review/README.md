# Getting Started with A2I

## 1. Set up A2I

Go through the steps in the notebook a2i_humanloop.ipynb 

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

## 3. Create the Human Post Processing lambba

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


```
