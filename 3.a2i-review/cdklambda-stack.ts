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
      fn.addEnvironment('preprocessingFunction','	arn:aws:lambda:us-east-1:077546553367:function:PreProcessImage:$LATEST');
      fn.addEnvironment('userid','us-east-1:073c31fb-efea-434d-ac4c-caccbce7d42a');

    
    
  }
}
