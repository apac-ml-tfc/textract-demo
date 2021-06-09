# OCR (Non-Amplify Services) Stack

This folder is where all our non-Amplify-managed resources are defined, including the OCR processing pipeline and the IoT-based progress notification components.

## Deploying Just the SAM Stack (No Amplify Front-End)

> *Can I deploy this without the Amplify app front end?*

**Yes!**

For some AWS Regions, we have pre-built CloudFormation stacks already available: Just click the buttons below and follow through the console workflow to deploy in your account.

| Region | Deployment Link |
|:------:|:---------------:|
| **ap-southeast-1** (Singapore) | [![Launch Stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://ap-southeast-1.console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=ocr-e2e-demo&templateURL=https://s3.ap-southeast-1.amazonaws.com/public-asean-textract-demo-ap-southeast-1/textract/ocr-stack.yml) |
| **us-east-1** (N. Virginia) | [![Launch Stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://us-east-1.console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=ocr-e2e-demo&templateURL=https://s3.us-east-1.amazonaws.com/public-asean-textract-demo-us-east-1/textract/ocr-stack.yml) |

**For other regions**, you'll need to download this source code and build the stack yourself:

- Install the [AWS SAM CLI](https://aws.amazon.com/serverless/sam/)
- Check out the example commands as Amplify runs them in the [Makefile](../Makefile)

The important differences will be:

- You don't need to specify Cognito user/ID pools if not linking to a front-end app.
- Recommend adding `--use-container` argument to the `sam build` command, to have it build your Lambdas in tidy Docker containers rather than requiring your system to have the right dependencies & versions installed.

AWS SAM:

- `build`s your Lambda function bundles with the libraries they depend on
- `package`s these bundles to an S3 bucket and produces a true [CloudFormation template](https://aws.amazon.com/cloudformation/) from the source SAM template ([template.sam.yml](template.sam.yml))
- `deploy`s your stack to CloudFormation - where you can see it in the [CloudFormation Console](https://console.aws.amazon.com/cloudformation/home)


## Component Architecture

### Step Functions Orchestration

In AWS Step Functions we define a **state machine** in [Amazon States Language](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-amazon-states-language.html) (see [StateMachine.asl.json](StateMachine.asl.json)): Comprising a set of **states** (steps) and transitions between them.

An **execution** is triggered with an **input JSON payload**, which is transformed by and passed between the states until some end condition is met.

Therefore this JSON [state machine data object](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-state-machine-data.html) **is the interface** between the different processing stages - and may include e.g. references to S3 URIs for bigger data objects.

Generally from the first (pre-processing) step onwards, we keep *adding keys* to our state machine data, rather than fully replacing the payload. This practice has its drawbacks (there's a [quota on maximum data size](https://docs.aws.amazon.com/step-functions/latest/dg/limits.html), after all); but can be helpful for experimentation/debugging.

An execution that's been through all stages might have a payload structure something like this (additional fields omitted):

```jsonc
// (Additional fields omitted)
{
    "Bucket": "Pre-processed image bucket",
    "Key": "Pre-processed image key",
    "S3Uri": "s3://{Bucket}/{Key}",
    "Input": {
        "Bucket": "Initial raw input bucket",
        "Key": "Initial raw input key",
        "S3Uri": "s3://{Input.Bucket}/{Input.Key}"
    },
    "Textract": {
        "Bucket": "Textract raw result bucket",
        "Key": "Textract raw result key",
        "S3Uri": "s3://{Textract.Bucket}/{Textract.Key}"
    },
    "ModelResult": {
        "Date": {
            "Confidence": 91.30914211273193,
            "Value": "21-06-2018 18:54:22"
        },
        "Total": {
            "Confidence": 34.79802322387695,
            "Value": "4.60"
        },
        "Vendor": {
            "Confidence": 99.73851013183594,
            "Value": "My Cool Restaura"
        },
        "Confidence": 34.79802322387695
    },
    "HumanReview": {
        "Date": "21-06-2018 18:54:22",
        "Vendor": "My Cool Restaurant",
        "Total": "4.60",
        "WorkerId": "abcdef1234567890"
    }
}
```

Although Step Functions offers a range of [direct integrations](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-service-integrations.html) to other AWS services, pretty much all our tasks are fronted by Lambda functions. This includes both synchronous (call the Lambda and return the result) and **asynchronous** (notify Step Functions with a token when complete) tasks.
