import json
import boto3
import os


def lambda_handler(event, context):
    ssmKey = event['detail']['name']

    client = boto3.client('ssm')
    response = client.get_parameter(Name=f"/{ssmKey}")
    ssmValue = response['Parameter']['Value']

    amiRegion = 'us-west-2'

    destRegion = 'us-west-2'
    destAccount = '<DESTINATION_ACCOUNT>'
    destAccountRole = 'arn:aws:iam::<DESTINATION_ACCOUNT>:role/crossAccountAMI-Role'

    # Set image permission
    client = boto3.client('ec2', region_name=amiRegion)
    client.modify_image_attribute(
        Attribute='launchPermission',
        ImageId=ssmValue,
        OperationType='add',
        UserIds=[destAccount]
    )

    # Get EBS volument associated with the image and it's permisssion
    image_details = client.describe_images(
        ImageIds=[
            ssmValue
        ],
        Owners=[
            'self'
        ]
    )

    snapshotId = image_details['Images'][0]['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
    client.modify_snapshot_attribute(
        Attribute='createVolumePermission',
        OperationType='add',
        SnapshotId=snapshotId,
        UserIds=[destAccount]
    )

    client = boto3.client('sts')
    getCred = client.assume_role(
        RoleArn=destAccountRole, RoleSessionName=destAccount)

    cred = getCred['Credentials']

    tempSession = boto3.Session(aws_access_key_id=cred['AccessKeyId'],
                                aws_secret_access_key=cred['SecretAccessKey'],
                                aws_session_token=cred['SessionToken'],
                                region_name=destRegion)
    client = tempSession.client('ec2', region_name=destRegion)
    client.copy_image(
        Name="Base Image",
        Description=f"Copy from Main account",
        SourceImageId=ssmValue,
        SourceRegion=amiRegion
    )

    return {
        'statusCode': 200,
        'body': json.dumps('AMI Copied successfully')
    }
