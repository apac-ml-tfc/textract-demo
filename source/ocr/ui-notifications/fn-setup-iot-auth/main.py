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
env_identity_pool_id = os.environ["COGNITO_IDENTITY_POOL_ID"]

IOT_TARGET_BATCH_SIZE = 250  # Max permitted per the API doc
IDENTITY_BATCH_SIZE = 60  # Max permitted per the API doc

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
        # (These params are common across Cognito trigger types)
        # It's a Cognito Lambda trigger request
        return new_user_handler(event, context)
    else:
        # Just interpret it as an instruction to refresh everybody's perms:
        attach_iot_policy_to_all_identities(env_identity_pool_id, env_iot_policy_name)
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Credentials": True,
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "Message": f"Updated IoT permissions for Cognito Identity pool {env_identity_pool_id}"
            }),
        }


def setup_stack_handler(event, context):
    identity_pool_id = event["ResourceProperties"]["CognitoIdentityPoolId"]
    user_pool_id = event["ResourceProperties"].get("CognitoUserPoolId")

    print(f"Granting IoT access for existing Cognito identities")
    try:
        attach_iot_policy_to_all_identities(
            identity_pool_id,
            event["ResourceProperties"].get("IotAccessPolicyName", env_iot_policy_name)
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
        try:
            current_fn_arn = context.invoked_function_arn
            #current_fn_version = context.function_version
            update_lambda_triggers(
                { "PostAuthentication": current_fn_arn },
                new_user_pool_id=user_pool_id,
            )
        except Exception as e:
            traceback.print_exc()
            return cfnresponse.send(
                event,
                context,
                "FAILED",
                {
                    "Error": "Failed to set up Lambda triggers on Cognito user pool ID {}\n{}: {}".format(
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

    # Refresh IoT policy attachments on the new pool even if there's been 'no change'
    if (identity_pool_id):
        try:
            attach_iot_policy_to_all_identities(identity_pool_id, iot_policy_name)
        except Exception as e:
            traceback.print_exc()
            # This is a failing error iff the update includes a change to the relevant components:
            if (identity_pool_id != old_identity_pool_id or iot_policy_name != old_iot_policy_name):
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
            else:
                print("Ignoring IoT policy refresh failure as cfn Update didn't edit pool ID or policy")

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

    if (
        old_identity_pool_id
        and (old_identity_pool_id != identity_pool_id or old_iot_policy_name != iot_policy_name)
    ):
        try:
            detach_iot_policy_from_all_identities(old_identity_pool_id: str, old_iot_policy_name: str)
        except Exception as e:
            traceback.print_exc()
            return cfnresponse.send(
                event,
                context,
                "FAILED",
                {
                    "Error": "Couldn't revoke IoT access policy from old identity pool.  {}: {}".format(
                        type(e).__name__,
                        str(e),
                    ),
                },
            )

    if (user_pool_id != old_user_pool_id):
        try:
            trigger_dict = { "PostAuthentication": context.invoked_function_arn }
            update_lambda_triggers(
                trigger_dict,
                new_user_pool_id=user_pool_id,
                old_user_pool_id=old_user_pool_id,
                # TODO: Handle changes in Lambda ARN by taking it as a parameter?
                #old_trigger_dict=None,
            )
        except Exception as e:
            traceback.print_exc()
            return cfnresponse.send(
                event,
                context,
                "FAILED",
                {
                    "Error": "Couldn't update user pool Lambda trigger configuration.  {}: {}".format(
                        type(e).__name__,
                        str(e),
                    ),
                },
            )


    return cfnresponse.send(
        event,
        context,
        "SUCCESS",
        { "Message": "Update complete" },
    )


def delete_stack_handler(event, context):
    identity_pool_id = event["ResourceProperties"]["CognitoIdentityPoolId"]
    user_pool_id = event["ResourceProperties"].get("CognitoUserPoolId")


    print(f"Revoking IoT access for existing Cognito identities")
    try:
        detach_iot_policy_from_all_identities(
            identity_pool_id,
            event["ResourceProperties"].get("IotAccessPolicyName", env_iot_policy_name)
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
        try:
            current_fn_arn = context.invoked_function_arn
            #current_fn_arn = context.function_version
            update_lambda_triggers(
                { "PostAuthentication": current_fn_arn },
                old_user_pool_id=user_pool_id,
            )
        except Exception as e:
            traceback.print_exc()
            return cfnresponse.send(
                event,
                context,
                "FAILED",
                {
                    "Error": "Unable to clear Lambda triggers from Cognito user pool ID {}\n{}: {}".format(
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
        { "Message": "Tear-down complete" },
    )


def post_login_handler(event, context):
    """On every user login, check the whole identity pool's setup

    Cognito User Pool triggers listen to the user pool, not the identity pool, so they don't see the
    IdentityId associated with the current UserId.

    Since our demo app will have a small pool of identities, it's more practical/easy to do this than set up
    a custom API for logged-in users to request their permissions be set up.

    TODO: Cognito triggers must respond in 5sec - add timeout or async process kick-off?
    """
    try:
        attach_iot_policy_to_all_identities(env_identity_pool_id, env_iot_policy_name)
    except Exception as e:
        traceback.print_exc()
        print("WARNING: failed to refresh pool IoT perms on user login - ignoring")
    return event


def attach_iot_policy_to_all_identities(identity_pool_id: str, iot_policy_name: str):
    """Lists all targets attached to the policy, and all identities in the pool, then reconciles"""

    print(f"Querying which identities are already attached to IoT policy {iot_policy_name}")
    already_attached_identities = set()
    iot_target_list = iot.list_targets_for_policy(
        policyName=os.environ['IOT_POLICY'],
        pageSize=IOT_TARGET_BATCH_SIZE,
    )
    while len(iot_target_list["targets"]):
        already_attached_identities.update(iot_target_list["targets"])
        next_token = iot_target_list["nextMarker"]
        if next_token:
            if len(iot_target_list["targets"]) < IOT_TARGET_BATCH_SIZE:
                print("WARNING: Got a continuation token but fewer than requested IoT targets???")
            iot_target_list = iot.list_targets_for_policy(
                policyName=os.environ['IOT_POLICY'],
                pageSize=IOT_TARGET_BATCH_SIZE,
                marker=next_token,
            )
        else:
            break

    print(f"Ensuring all identities in {identity_pool_id} attached to IoT policy {iot_policy_name}")
    identity_list = cognito_identity.list_identities(
        IdentityPoolId=identity_pool_id,
        MaxResults=IDENTITY_BATCH_SIZE,
    )
    while len(identity_list["Identities"]):
        for identity in identity_list["Identities"]:
            if identity["IdentityId"] not in already_attached_identities:
                iot.attach_policy(policyName=iot_policy_name, target=identity["IdentityId"])
        next_token = identity_list.get("NextToken")
        if next_token:
            if len(identity_list["Identities"]) < IDENTITY_BATCH_SIZE:
                print("WARNING: Got a continuation token but fewer than requested identities???")
            identity_list = cognito_identity.list_identities(
                IdentityPoolId=identity_pool_id,
                MaxResults=IDENTITY_BATCH_SIZE,
                NextToken=next_token,
            )
        else:
            break


def detach_iot_policy_from_all_identities(identity_pool_id: str, iot_policy_name: str):
    print(f"Revoking IoT access for existing Cognito identities")
    identity_list = cognito_identity.list_identities(
        IdentityPoolId=identity_pool_id,
        MaxResults=IDENTITY_BATCH_SIZE,
    )
    while len(identity_list["Identities"]):
        for identity in identity_list["Identities"]:
            # This doesn't seem to raise an exception if already detached:
            iot.detach_policy(policyName=iot_policy_name, target=identity["IdentityId"])
        next_token = identity_list.get("NextToken")
        if next_token:
            if len(identity_list["Identities"]) < IDENTITY_BATCH_SIZE:
                print("WARNING: Got a continuation token but fewer than requested identities???")
            identity_list = cognito_identity.list_identities(
                IdentityPoolId=identity_pool_id,
                MaxResults=IDENTITY_BATCH_SIZE,
                NextToken=next_token,
            )
        else:
            break


def update_lambda_triggers(
    trigger_dict,
    new_user_pool_id=None,
    old_user_pool_id=None,
    old_trigger_dict=None,
):
    """Install triggers from new_user_pool_id and/or clean from old_user_pool_id

    trigger_dict is a dict from event to Lambda function ARN, as per:
    https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_UpdateUserPool.html

    If old_trigger_dict is not specified, the same spec will be used between setup and cleaning

    TODO: Tolerate previous versions of the same function, or aliases, or etc
    """
    if old_trigger_dict is None:
        old_trigger_dict = trigger_dict
    # First install on the new pool, if present:
    if new_user_pool_id:
        print(f"Setting Lambda triggers on new Cognito user pool {new_user_pool_id}")
        new_pool_desc = cognito_idp.describe_user_pool(UserPoolId=new_user_pool_id)
        existing_triggers = new_pool_desc["UserPool"].get("LambdaConfig", {})
        updated_triggers = existing_triggers.copy()  # This will be our update request
        any_changes = False  # Tracking whether an update is needed at all
        for key in trigger_dict:
            prev_trigger = existing_triggers.get(key)

            if trigger_dict[key]:
                updated_triggers[key] = trigger_dict[key]
            elif key in updated_triggers:
                del updated_triggers[key]  # a ""/None entry in trigger_dict should explicitly delete.

            if trigger_dict[key] != prev_trigger:
                any_changes = True
                if prev_trigger:
                    raise ValueError(
                        f"Trigger '{key}' already configured to different function {prev_trigger}"
                    )
        if any_changes:
            cognito_idp.update_user_pool(
                UserPoolId=new_user_pool_id,
                LambdaConfig=updated_triggers,
            )

    # Then remove from old pool, if present:
    if old_user_pool_id:
        print(f"Clearing Lambda triggers from old Cognito user pool {old_user_pool_id}")
        new_pool_desc = cognito_idp.describe_user_pool(UserPoolId=old_user_pool_id)
        existing_triggers = new_pool_desc["UserPool"].get("LambdaConfig", {})
        updated_triggers = existing_triggers.copy()  # This will be our update request
        any_changes = False  # Tracking whether an update is needed at all
        for key in old_trigger_dict:
            if old_trigger_dict[key] and old_trigger_dict[key] == existing_triggers.get(key):
                any_changes = True
                del updated_triggers[key]
        if any_changes:
            cognito_idp.update_user_pool(
                UserPoolId=old_user_pool_id,
                LambdaConfig=updated_triggers,
            )
