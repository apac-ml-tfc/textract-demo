##########################
# Bootstrapping variables
##########################

AWS_BRANCH ?= "dev"
STACK_NAME ?= "UNDEFINED"
DEPLOYMENT_BUCKET_NAME ?= "UNDEFINED"
UPLOAD_BUCKET_NAME ?= "UNDEFINED"
COGNITO_IDENTITY_POOL_ID ?= "UNDEFINED"
COGNITO_USER_POOL_ID ?= "UNDEFINED"
SAM_BUILD_EXTRA_ARGS ?= ""

target:
	$(info ${HELP_MESSAGE})
	@exit 0

init: ##=> Install OS deps and dev tools
	$(info [*] Bootstrapping CI system...)
	@$(MAKE) _install_os_packages

deploy: ##=> Deploy services
	$(info [*] Deploying...)
	$(MAKE) deploy.processing

delete: ##=> Delete services
	$(MAKE) delete.processing

delete.processing: ##=> Delete OCR processing service
	aws cloudformation delete-stack --stack-name $${STACK_NAME}-processing-$${AWS_BRANCH}

deploy.processing: ##=> Deploy OCR processing service using SAM
	$(info [*] Packaging and deploying OCR processing service...)
	cd source/ocr && \
		sam build \
			--template template.sam.yml \
			$(SAM_BUILD_EXTRA_ARGS) && \
		sam package \
			--s3-bucket $${DEPLOYMENT_BUCKET_NAME} \
    	--s3-prefix sam \
			--output-template-file template-packaged.tmp.yml && \
		sam deploy \
			--template-file template-packaged.tmp.yml \
			--stack-name $${STACK_NAME}-processing-$${AWS_BRANCH} \
			--capabilities CAPABILITY_IAM \
			--no-fail-on-empty-changeset \
			--parameter-overrides \
				UploadBucketName=$${UPLOAD_BUCKET_NAME} \
				CognitoIdentityPoolId=$${COGNITO_IDENTITY_POOL_ID} \
				CognitoUserPoolId=$${COGNITO_USER_POOL_ID}
		# 	BookingTable=/$${AWS_BRANCH}/service/amplify/storage/table/booking \
		# 	FlightTable=/$${AWS_BRANCH}/service/amplify/storage/table/flight \
		# 	CollectPaymentFunction=/$${AWS_BRANCH}/service/payment/function/collect \
		# 	RefundPaymentFunction=/$${AWS_BRANCH}/service/payment/function/refund \
		# 	AppsyncApiId=/$${AWS_BRANCH}/service/amplify/api/id \
		# 	Stage=$${AWS_BRANCH}

export.parameter:
	$(info [+] Adding new parameter named "${NAME}")
	aws ssm put-parameter \
		--name "$${NAME}" \
		--type "String" \
		--value "$${VALUE}" \
		--overwrite

#############
#  Helpers  #
#############

_install_os_packages:
	$(info [*] Installing jq...)
	yum install jq -y
	$(info [*] Checking currently installed Python version...)
	python3 --version
	# This didn't work and installed version looks like 3.7 - let's just change our Lambdas to use 3.7 runtime:
	# $(info [*] Installing Python v3.8...)
	# pwd
	# cd /opt
	# wget --no-verbose https://www.python.org/ftp/python/3.8.3/Python-3.8.3.tgz
	# tar xzf Python-3.8.3.tgz
	# cd Python-3.8.3
	# ./configure --enable-optimizations
	# make altinstall
	# rm -f /opt/Python-3.8.3.tgz
	# python3.8 --version
	$(info [*] Upgrading Python SAM CLI and CloudFormation linter to the latest version...)
	python3 -m pip install --upgrade --user cfn-lint aws-sam-cli
	npm -g install aws-cdk

define HELP_MESSAGE

	Environment variables:

	These variables are automatically filled at CI time except STRIPE_SECRET_KEY
	If doing a dirty/individual/non-ci deployment locally you'd need them to be set

	AWS_BRANCH: "dev"
		Description: Feature branch name used as part of stacks name; added by Amplify Console by default
	FLIGHT_TABLE_NAME: "Flight-hnxochcn4vfdbgp6zaopgcxk2a-xray"
		Description: Flight Table name created by Amplify for Catalog service
	STACK_NAME: "awsserverlessairline-twitch-20190705130553"
		Description: Stack Name already deployed; used for dirty/individual deployment
	DEPLOYMENT_BUCKET_NAME: "a_valid_bucket_name"
		Description: S3 Bucket name used for deployment artifacts
	GRAPHQL_API_ID: "hnxochcn4vfdbgp6zaopgcxk2a"
		Description: AppSync GraphQL ID already deployed
	BOOKING_TABLE_NAME: "Booking-hnxochcn4vfdbgp6zaopgcxk2a-xray"
		Description: Flight Table name created by Amplify for Booking service
	STRIPE_SECRET_KEY: "sk-test-asdf..."
		Description: Stripe Private Secret Key generated in Stripe; manually added in Amplify Console Env Variables per App

	Common usage:

	...::: Bootstraps environment with necessary tools like SAM CLI, cfn-lint, etc. :::...
	$ make init

	...::: Deploy all SAM based services :::...
	$ make deploy

	...::: Delete all SAM based services :::...
	$ make delete

	...::: Export parameter and its value to System Manager Parameter Store :::...
	$ make export.parameter NAME="/env/service/amplify/api/id" VALUE="xzklsdio234"
endef
