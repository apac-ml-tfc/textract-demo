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
# copy and replace contents from textract-demo/4.web-gui into smartocr folder
```

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
* AWS profile: <use appropriate AWS profile>

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
* bucket name: smartocr-uploads
* who should have access: Auth users only
* access: create/update, read
* add Lambda trigger: N

### Update CloudFormation stacks
```
amplify push
```

## TODO: other AWS assets here

### IoT Core endpoint for pubsub

### dynamodb table

### lambda ocr function

### s3 image upload trigger

### preprocessing lambda function

### a2i config

### post a2i lambda trigger

## Run app

### Compile and run dev server locally
```
npm run serve
```

### Deploy to AWS Amplify Hosting
```
amplify add hosting
```
* Amplify hosting
```
amplify publish
```
## Login to app

## Cleanup project
```
amplify delete
```
These objects must be deleted explicitly
* S3 bucket
