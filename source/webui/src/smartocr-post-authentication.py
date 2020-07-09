import json
import boto3
import os

def lambda_handler(event, context):

  cognito= boto3.client('cognito-identity')
  identitylist = cognito.list_identities(
    IdentityPoolId=os.environ['IDENTITY_POOLID'],
    MaxResults=10,
    HideDisabled=True
  )
  
  iot = boto3.client('iot')
  targets = iot.list_targets_for_policy(
      policyName=os.environ['IOT_POLICY']
  )
  
  #print('Targets:', targets)
  attached = []
  
  for i in targets["targets"]:
    attached.append(i.split(':',1)[1])
    
  #print('Attached: ', attached)
  
  for i in identitylist["Identities"]:
    id = i["IdentityId"]
    cnt = attached.count(id)
    if(cnt==0):
      print('attaching: ', id)
      out = iot.attach_policy(
        policyName='myIoTPolicy',
        target=i["IdentityId"]
      )
  # Send post authentication data to Cloudwatch logs
  print ("Authentication successful")
  
  # Return to Amazon Cognito
  return event


