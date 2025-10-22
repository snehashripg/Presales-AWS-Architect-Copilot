from awslabs.challenge import Challenge
import boto3
import os
import click
from botocore.vendored import requests
from botocore.exceptions import ClientError


STACK_NAME = "awslabs-vpc-test"


class MyChallenge(Challenge):
    """
    Now our VPC is ready to deploy some workloads. A CloudFormation
    template is copied to the current directory. Review this template to
    quickly learn how an instance is deployed in your VPC.

    Tasks:
    - if you created a CloudFormation template: Define Outputs for
      `vpc` and `public-subnet-1`. Here's an example:

      Outputs:
        Vpc:
            Value: !Ref Vpc
            Export:
            Name: vpc
        PublicSubnet1:
            Value: !Ref PublicSubnet1
            Export:
            Name: public-subnet-1

    - Deploy the template with stack name: `awslabs-vpc-test`.
    - Find the instance's public IP address. From the command line:

      aws ec2 describe-instances | grep PublicIpAddress

    - Open the IP address in a browser and the "Amazon Linux AMI Test Page"
      should show up.
    """

    title = "Test your Stack"
    description = __doc__

    def start(self):
        provide_stack()
        self.instructions()


    def validate(self):

        instance = self.ec2_instance()

        ip = instance["PublicIpAddress"]

        response = requests.get("http://{}".format(ip))

        print (type(response.content))
        if "Amazon Linux AMI" not in str(response.content):
            self.fail("Could not find a web page at http://{}.".format(ip))

        self.success("Awesome! You have a server running on your hand-crafted VPC.")


    def ec2_instance(self):
        cfn = boto3.client("cloudformation")
        ec2 = boto3.client("ec2")

        try:
            resources = cfn.describe_stack_resources(StackName=STACK_NAME)["StackResources"]
        except ClientError as e:
            self.fail("Could not find Cloudformation resources: {}".format(e))

        try:
            instance_id = [r["PhysicalResourceId"] for r in resources if r["ResourceType"] == "AWS::EC2::Instance"][0]
        except IndexError:
           self.fail("Could not find AWS::EC2::Instance resource in Cloudformation stack {}".format(STACK_NAME))

        try:
            instance = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
        except (IndexError, KeyError):
            self.fail("The instance resource could not be found in EC2")

        return instance

def provide_stack():
    stack_file = "vpc_test_stack.yml"
    if os.path.exists(stack_file):
        print("There's already a file named {}.".format(stack_file))
        return
    stack = open(stack_file, "w")
    stack.write(STACK_YAML)
    stack.close()


STACK_YAML = """AWSTemplateFormatVersion: '2010-09-09'
Description: AWSlabs VPC Challenge Example VM

# If you uses CloudFormation you're in luck: export your vpc id and
# the 1st public subnet as "public-subnet-1" from your template.
# Use the snippet below for inspiration. If you do not have used
# CloudFormation, find the VPC and Subnet Id's, and provide them
# as parameters. Fix the `!Ref` lines in the template.
#
# Outputs:
#   Vpc:
#     Value: !Ref Vpc
#     Export:
#       Name: vpc
#   PublicSubnet1:
#     Value: !Ref PublicSubnet1
#     Export:
#       Name: public-subnet-1

Parameters:
  AmazonAmiId:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/amzn-ami-hvm-x86_64-gp2
  SubnetId:
    Type: String
    Default: " ** Put Subnet ID instead of this string** "

Resources:
  Instance:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: t2.micro
      ImageId: !Ref AmazonAmiId
      NetworkInterfaces:
        - AssociatePublicIpAddress: true
          DeviceIndex: "0"
          GroupSet:
            - !Ref InstanceSecurityGroup
          # NB. If you did use CloudFormation:
          SubnetId: !ImportValue public-subnet-1
          # If not, comment out the previous line and comment out this line:
          # SubnetId: !Ref SubnetId
      UserData:
        Fn::Base64: !Sub |
          #!/bin/bash
          yum -y update
          yum -y install httpd
          /usr/sbin/apachectl start

  InstanceSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Allow http to client host
      # NB. If you did use CloudFormation:
      VpcId: !ImportValue vpc
      # If not, comment out the previous line and comment out this line:
      # VpcId: !Ref Vpc
      SecurityGroupIngress:
      - IpProtocol: tcp
        FromPort: 80
        ToPort: 80
        CidrIp: 0.0.0.0/0
      SecurityGroupEgress:
      - IpProtocol: tcp
        FromPort: 80
        ToPort: 80
        CidrIp: 0.0.0.0/0
"""
