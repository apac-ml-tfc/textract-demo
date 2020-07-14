# OCR (Non-Amplify Services) Stack

This folder is where all our non-Amplify-managed resources are defined, including the OCR processing pipeline and the IoT-based progress notification components.

## Deploying Just the SAM Stack (No Amplify Front-End)

> *Can I deploy this without the Amplify app front end?*

**Yes!**

- Install the [AWS SAM CLI](https://aws.amazon.com/serverless/sam/)
- Check out the example commands as Amplify runs them in the [Makefile](../Makefile)

The important differences will be:

- You don't need to specify Cognito user/ID pools if not linking to a front-end app.
- Recommend adding `--use-container` argument to the `sam build` command, to have it build your Lambdas in tidy Docker containers rather than requiring your system to have the right dependencies & versions installed.

AWS SAM:

- `build`s your Lambda function bundles with the libraries they depend on
- `package`s these bundles to an S3 bucket and produces a true [CloudFormation template](https://aws.amazon.com/cloudformation/) from the source SAM template ([template.sam.yml](template.sam.yml))
- `deploy`s your stack to CloudFormation - where you can see it in the [CloudFormation Console](https://console.aws.amazon.com/cloudformation/home)
