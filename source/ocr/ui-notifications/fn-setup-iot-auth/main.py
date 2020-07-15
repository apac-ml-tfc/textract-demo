"""Lambda to manage IoT PubSub permissions for OCR progress push notifications

Invokable as both a CloudFormation custom resource (to configure initial access) and a Cognito
PostConfirmation trigger (to add newly registering users).

TODO: PostConfirmation trigger not yet able to add new user access 
^ Because of: https://forums.aws.amazon.com/thread.jspa?messageID=924345

TODO: Implement 'Update' action for CloudFormation (currently just Create and Delete supported)

"""

# Python Built-Ins:
import os
import time
import traceback

# External Dependencies:
import boto3

# Local Dependencies:
import cfnresponse  # AWS CloudFormation response util

iam = boto3.client("iam")
iot = boto3.client("iot")
cognito_identity = boto3.client("cognito-identity")
cognito_idp = boto3.client("cognito-idp")

# We pass this in as *both* a CF resource param and a Lambda env var because the Lambda function may need the
# information for other invokations besides CF, but for edge-case CF calls (e.g. update stack) the resource
# prop should be authoritative:
env_iot_policy_name = os.environ["IOT_ACCESS_POLICY_NAME"]

def handler(event, context):
    # Determine if it's a CloudFormation resource request (set up or tear-down) or a Cognito request
    # (configure new user)
    # CF request object reference here:
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-requests.html
    if "RequestType" in event and "StackId" in event:
        # It's a CloudFormation request
        try:
            # Check required resource properties:
            if "ResourceProperties" not in event or "CognitoUserPoolId" not in event["ResourceProperties"]:
                return cfnresponse.send(
                    event,
                    context,
                    "FAILED",
                    { "Error": "Missing required resource property 'CognitoUserPoolId'" },
                )

            if event["RequestType"] == "Create":
                return setup_stack_handler(event, context)
            elif event["RequestType"] == "Update":
                return update_stack_handler(event, context)
            elif event["RequestType"] == "Delete":
                return delete_stack_handler(event, context)
            else:
                return cfnresponse.send(
                    event,
                    context,
                    "FAILED",
                    {
                        "Error": f"Got unexpected RequestType '{event['RequestType']}' from CloudFormation",
                    },
                )
        except Exception as e:
            traceback.print_exc()
            return cfnresponse.send(
                event,
                context,
                "FAILED",
                { "Error": f"Uncaught exception {traceback.format_exc()}" },
            )
    elif "triggerSource" in event and "userName" in event:
        # It's a Cognito Lambda trigger request
        return new_user_handler(event, context)
    else:
        raise ValueError(f"Unknown event structure: {event}")


def setup_stack_handler(event, context):
    identity_pool_id = event["ResourceProperties"]["CognitoIdentityPoolId"]
    user_pool_id = event["ResourceProperties"].get("CognitoUserPoolId")

    print(f"Setting up identity pool {identity_pool_id}")
    try:
        identity_pool_roles = cognito_identity.get_identity_pool_roles(IdentityPoolId=identity_pool_id)
        authenticated_role_arn = identity_pool_roles["Roles"]["authenticated"]
        authenticated_role_name = authenticated_role_arn.rpartition("/")[2]
    except Exception as e:
        try:
            print(identity_pool_roles)
        except NameError:
            pass
        traceback.print_exc()
        return cfnresponse.send(
            event,
            context,
            "FAILED",
            { "Error": f"Couldn't find authenticated role for Cognito identity pool ID {identity_pool_id}" },
        )

    # TODO: Delete and Update actions for identity pool
    print(f"Attaching AWSIoTConfigAccess and AWSIoTDataAccess to {authenticated_role_name}")
    try:
        # TODO: Does this raise an exception if already attached?
        iam.attach_role_policy(
            RoleName=authenticated_role_name,
            PolicyArn="arn:aws:iam::aws:policy/AWSIoTConfigAccess",
        )
        iam.attach_role_policy(
            RoleName=authenticated_role_name,
            PolicyArn="arn:aws:iam::aws:policy/AWSIoTDataAccess",
        )
    except Exception as e:
        traceback.print_exc()
        return cfnresponse.send(
            event,
            context,
            "FAILED",
            {
                "Error": "Couldn't attach AWSIoTConfigAccess and AWSIoTDataAccess to role {}  {}: {}".format(
                    authenticated_role_name,
                    type(e).__name__,
                    str(e),
                ),
            },
        )

    print(f"Granting IoT access for existing Cognito identities")
    try:
        # TODO: Pagination loop
        identity_list = cognito_identity.list_identities(
            IdentityPoolId=identity_pool_id,
            MaxResults=60,  # Max permitted per the API doc
        ) #, NextToken="")
        print(identity_list)
        for identity in identity_list["Identities"]:
            # TODO: Does this raise an exception if already attached?
            iot.attach_policy(
                policyName=event["ResourceProperties"].get("IotAccessPolicyName", env_iot_policy_name),
                target=identity["IdentityId"],
            )
    except Exception as e:
        traceback.print_exc()
        return cfnresponse.send(
            event,
            context,
            "FAILED",
            {
                "Error": "Couldn't attach IoT access policy to existing identities.  {}: {}".format(
                    type(e).__name__,
                    str(e),
                ),
            },
        )


    if not user_pool_id:
        print(f"Skipping user pool Lambda trigger setup - no user pool ID provided")
    else:
        print(f"Setting up Lambda trigger on user pool {user_pool_id}")
        try:
            user_pool_desc = cognito_idp.describe_user_pool(UserPoolId=user_pool_id)
        except Exception as e:
            traceback.print_exc()
            return cfnresponse.send(
                event,
                context,
                "FAILED",
                {
                    "Error": "Unable to query Cognito user pool ID {}\n{}: {}".format(
                        user_pool_id,
                        type(e).__name__,
                        str(e),
                    ),
                },
            )

        current_fn_arn = context.invoked_function_arn
        #current_fn_arn = context.function_version
        existing_lambda_trigger = user_pool_desc["UserPool"].get("LambdaConfig", {}).get("PostConfirmation")
        # TODO: Tolerate previous versions of the same function, or aliases, or etc
        if existing_lambda_trigger:
            if existing_lambda_trigger != current_fn_arn:
                return cfnresponse.send(
                    event,
                    context,
                    "FAILED",
                    {
                        "Error": "Lambda PostConfirmation trigger already set for {} on user pool {}".format(
                            existing_lambda_trigger,
                            user_pool_id,
                        ),
                    },
                )
            # Else Lambda trigger is already set - no user pool configuration required.
        else:
            # Lambda trigger not yet set up - configure it:
            try:
                # The UpdateUserPool update is at LambdaConfig level, not at individual trigger level, so we
                # need to re-submit any other existing triggers to preserve them:
                existing_lambda_config = user_pool_desc["UserPool"].get("LambdaConfig", {})
                new_lambda_config = {
                    k: existing_lambda_config[k] for k in existing_lambda_config if k != "PostConfirmation"
                }
                new_lambda_config["PostConfirmation"] = current_fn_arn
                cognito_idp.update_user_pool(
                    UserPoolId=user_pool_id,
                    LambdaConfig=new_lambda_config,
                )
            except Exception as e:
                return cfnresponse.send(
                    event,
                    context,
                    "FAILED",
                    {
                        "Error": "Unable to set Lambda trigger on Cognito User Pool {}\n{}: {}".format(
                            user_pool_id,
                            type(e).__name__,
                            str(e),
                        ),
                    },
                )

    return cfnresponse.send(
        event,
        context,
        "SUCCESS",
        { "Message": "Setup complete" },
    )


def update_stack_handler(event, context):
    identity_pool_id = event["ResourceProperties"]["CognitoIdentityPoolId"]
    user_pool_id = event["ResourceProperties"].get("CognitoUserPoolId", "")
    iot_policy_name = event["ResourceProperties"].get("IotAccessPolicyName", env_iot_policy_name)
    old_props = event["OldResourceProperties"]
    old_identity_pool_id = old_props["CognitoIdentityPoolId"]
    old_user_pool_id = old_props.get("CognitoUserPoolId", "")
    old_iot_policy_name = event["ResourceProperties"].get("IotAccessPolicyName", env_iot_policy_name)

    if (
        identity_pool_id == old_identity_pool_id
        and user_pool_id == old_user_pool_id
        and iot_policy_name == old_iot_policy_name
    ):
        print("Null update - nothing to change")
        return cfnresponse.send(
            event,
            context,
            "SUCCESS",
            { "Message": "Nothing to update" },
        )
    else:
        # TODO: Implement update and make success less permissive
        print("NOT IMPLEMENTED: CloudFormation stack update with param changes")
        return cfnresponse.send(
            event,
            context,
            "SUCCESS",
            { "Error": "CloudFormation Update method not yet implemented" },
        )


def delete_stack_handler(event, context):
    identity_pool_id = event["ResourceProperties"]["CognitoIdentityPoolId"]
    user_pool_id = event["ResourceProperties"].get("CognitoUserPoolId")

    print(f"Detaching from identity pool {identity_pool_id}")
    print(f"Detaching AWSIoTConfigAccess and AWSIoTDataAccess from authenticated role")
    try:
        identity_pool_roles = cognito_identity.get_identity_pool_roles(IdentityPoolId=identity_pool_id)
        authenticated_role_arn = identity_pool_roles["Roles"]["authenticated"]
        authenticated_role_name = authenticated_role_arn.rpartition("/")[2]
        try:
            iam.detach_role_policy(
                RoleName=authenticated_role_name,
                PolicyArn="arn:aws:iam::aws:policy/AWSIoTConfigAccess",
            )
        except iam.exceptions.NoSuchEntityException:
            pass
        try:
            iam.detach_role_policy(
                RoleName=authenticated_role_name,
                PolicyArn="arn:aws:iam::aws:policy/AWSIoTDataAccess",
            )
        except iam.exceptions.NoSuchEntityException:
            pass
    except cognito_identity.exceptions.ResourceNotFoundException:
        print(f"Identity pool not found - skipping: {identity_pool_id}")
    except Exception as e:
        try:
            print(identity_pool_roles)
        except NameError:
            pass
        traceback.print_exc()
        return cfnresponse.send(
            event,
            context,
            "FAILED",
            { "Error": f"Couldn't find authenticated role for Cognito identity pool ID {identity_pool_id}" },
        )


    print(f"Revoking IoT access for existing Cognito identities")
    try:
        # TODO: Pagination loop
        identity_list = cognito_identity.list_identities(
            IdentityPoolId=identity_pool_id,
            MaxResults=60,  # Max permitted per the API doc
        ) #, NextToken="")
        print(identity_list)
        for identity in identity_list["Identities"]:
            # TODO: Does this raise an exception if already detached?
            iot.detach_policy(
                policyName=event["ResourceProperties"].get("IotAccessPolicyName", env_iot_policy_name),
                target=identity["IdentityId"],
            )
    except Exception as e:
        traceback.print_exc()
        return cfnresponse.send(
            event,
            context,
            "FAILED",
            {
                "Error": "Couldn't detach IoT access policy from existing identities.  {}: {}".format(
                    type(e).__name__,
                    str(e),
                ),
            },
        )


    if not user_pool_id:
        print(f"Skipping user pool Lambda trigger cleanup - no user pool ID provided")
    else:
        print(f"Clearing Lambda trigger on user pool {user_pool_id}")
        try:
            # TODO: Succeed if user pool already deleted
            user_pool_desc = cognito_idp.describe_user_pool(UserPoolId=user_pool_id)
        except Exception as e:
            traceback.print_exc()
            return cfnresponse.send(
                event,
                context,
                "FAILED",
                {
                    "Error": "Unable to query Cognito user pool ID {}\n{}: {}".format(
                        user_pool_id,
                        type(e).__name__,
                        str(e),
                    ),
                },
            )

        current_fn_arn = context.invoked_function_arn
        #current_fn_arn = context.function_version
        existing_lambda_trigger = user_pool_desc["UserPool"].get("LambdaConfig", {}).get("PostConfirmation")
        # TODO: Tolerate previous versions of the same function, or aliases, or etc
        if existing_lambda_trigger:
            if existing_lambda_trigger == current_fn_arn:
                try:
                    # We're not allowed to explicitly set "PostConfirmation": "" or None or etc, so instead
                    # we'll call update with any existing triggers and explicitly *removing* the
                    # PostConfirmation key:
                    existing_lambda_config = user_pool_desc["UserPool"].get("LambdaConfig", {})
                    new_lambda_config = {
                        k: existing_lambda_config[k]
                        for k in existing_lambda_config if k != "PostConfirmation"
                    }
                    cognito_idp.update_user_pool(
                        UserPoolId=user_pool_id,
                        LambdaConfig=new_lambda_config,  # None is not permitted
                    )
                except Exception as e:
                    traceback.print_exc()
                    return cfnresponse.send(
                        event,
                        context,
                        "FAILED",
                        {
                            "Error": "Unable to clear user pool Lambda trigger {}\n{}: {}".format(
                                user_pool_id,
                                type(e).__name__,
                                str(e),
                            ),
                        },
                    )
            else:
                print("User pool Lambda trigger does not match current function - leaving as-is: {}".format(
                    existing_lambda_trigger,
                ))
        else:
            print("User pool does not have Lambda trigger set up - leaving as-is")

    return cfnresponse.send(
        event,
        context,
        "SUCCESS",
        { "Message": "Tear-down complete" },
    )


def new_user_handler(event, context):
    # TODO: Set up the user's account
    # Cognito triggers are supposed to modify and pass-through the same event object:
    print(event)
    return event
