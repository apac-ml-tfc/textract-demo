# Web GUI Flow
<br>![alt text ](https://github.com/apac-ml-tfc/textract-demo/blob/master/4.web-gui/webui-flow.png "Service flow") 

# Setup Web GUI environment

## Prerequisites

Before we begin, make sure you have the following installed:

* [Node.js](https://nodejs.org/) v10.x or later
* [npm](https://www.npmjs.com/) v5.x or later
* [git](https://git-scm.com/) v2.14.1 or later

## Install Amplify, Vue and app code

### Install and configure Amplify CLI
```
npm install -g @aws-amplify/cli
```

### Configure Amplify CLI with AWS IAM user keys
```
amplify configure
```
This creates the following files:
* ~/.aws/config
* ~/.aws/credentials

### Install Vue CLI
```
npm install -g @vue/cli
```

### Create new project
```
vue create smartocr
```
This creates a smartocr folder.

### Extract app code 
```
git clone https://github.com/apac-ml-tfc/textract-demo.git
cd smartocr
```
Copy and replace contents from <b>textract-demo/4.web-gui</b> into <b>smartocr</b> folder

### Install app required npm modules in the app folder
```
cd smartocr
npm install --save bootstrap bootstrap-vue
npm install --save aws-amplify aws-amplify-vue
```

### Initialize Amplify
```
amplify init
```
* project name: smartocr
* env name: dev
* default editor: Visual Studio Code
* type of app: javascript
* javascript framework: vue
* src dir path: src
* distribution dir path: ist
* build command: npm run-script build
* start command: npm run-script serve
* using default provider: awscloudformation (can’t change)
* AWS profile: use default or new profile

### Adds S3 storage with Cognito Authentication and Authorization
```
amplify add storage
```
* Content (Images, audio, video, etc)
* add auth now: Y
* default authentication and security configuration: Default configuration
* How do you want users to be able to sign in: Username
* Advanced settings: N
* Resource friendly name: smartocr
* bucket name: <b>smartocr-uploads</b>
* who should have access: Auth users only
* access: create/update, read
* add Lambda trigger: N

### Update cloud resources
Run the following command to check Amplify's status:
```
amplify status
```
This will show the current status of the Amplify project, including the current environment, any categories that have been created, and what state those categories are in.

Run the following command to update the cloud resources.
```
amplify push
```

## Setup additional AWS services

### IoT Core endpoint for pubsub

#### Obtain the IoT Core endpoint
```
aws iot describe-endpoint
```
Update the region and endpoint values in <b>src/SmartOCR.vue</b>
```
const AWS_PUBSUB_REGION = 'us-east-1'
const AWS_PUBSUB_ENDPOINT = 'wss://ENDPOINTHERE/mqtt'
```
#### Create IoT Policy
To use PubSub with AWS IoT, you will need to create an IoT Policy in the AWS IoT Console, and attach this policy to each logged-in user's Cognito Identity. This attachment is performed after a Cognito user is authenticated.

Go to [IoT Core](https://console.aws.amazon.com/iot/home) and choose <b>Secure</b> from the left navigation pane. Then navigate to <b>Policies</b> and create the following policy:
* Name: <b>myIoTPolicy</b>
* Action: iot:*
* Resource ARN: arn:aws:iot:YOUR-IOT-REGION:YOUR-IOT-ACCOUNT-ID:*
* Effect: Allow

Note: the policy name must match the name used in the following Lambda function.
#### Attach IoT policy to Amazon Cognito Identity
Create a new [Lambda function](https://console.aws.amazon.com/lambda) with Function code from <b>src/smartocr-post-authentication.py</b>
* Function name: <b>smartocr-post-authentication</b>
* Runtime: Python 3.8
* Execution role: Create a new role with basic Lambda permissions

After function is created, go to <b>Permissions</b> tab to open the role (e.g. smartocr-post-authentication-role-e73v7toi), and attach the following policies:
* AWSIoTConfigAccess
* AmazonCognitoPowerUser

In IAM, search for <b>amplify-smartocr</b> and select the role that ends with <b>authRole</b>. This role was created by Amplify and assumed by authenticated users. Attach the following policies:
* AWSIoTConfigAccess
* AWSIotDataAccess

Go to [Cognito User Pool](https://console.aws.amazon.com/cognito/users) and choose <b>Triggers</b> from the left navigation pane. In the <b>Post authentication panel</b>, select the Lambda function created previously:
```
smartocr-post-authentication
```


### S3 image upload trigger
Complete setup in [2.ocr-post-processing](https://github.com/apac-ml-tfc/textract-demo/tree/master/2.ocr-post-processing) and note Lambda function name.

Go to [S3](https://console.aws.amazon.com/s3) and select <b>smartocr-uploads*</b> bucket. In the <b>Properties</b> tab select <b>Events</b> and add the following notification:
* Name: smartocr-s3objectcreate
* Events: All object create events
* Send to: Lambda Function
* Lambda: <b>Select the Lambda function defined in ocr-post-processing</b>

### Post A2I lambda trigger
Complete setup in [3.a2i-review](https://github.com/apac-ml-tfc/textract-demo/tree/master/3.a2i-review)

## Run app

### Compile and run dev server locally
```
npm run serve
```

If you are running this in an AWS Cloud9 environment, replace following content in the <b>vue.config.js</b> file
```
    #public: 'http://localhost:8080’
    public: 'https://xxxxxxxxxxxx.vfs.cloud9.us-east-1.amazonaws.com'
```

### Login to app

You may now login to the app on your local machine. On the home page, create an account with a valid email address for email confirmation. Login with the your credentials and try uploading samples from this folder.

### Add hosting to your app
Perform the following to deploy your app manually. You may choose to setup automatic continuous deployment.
```
amplify add hosting
```
* plugin module: Hosting with Amplify Console
* type: Manual deployment

### Publish app

```
amplify publish
```
Note the published url, e.g. xvxvxvxvxvxvxv.amplifyapp.com

## Cleanup project
```
amplify delete
```
These objects must be deleted explicitly
* S3 buckets
