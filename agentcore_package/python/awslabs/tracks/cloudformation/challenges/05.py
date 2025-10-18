from awslabs.challenge import Challenge
import boto3
import os
import yaml
import click
from cfn_tools.yaml_loader import CfnYamlLoader, ODict


class MyChallenge(Challenge):

    title = "Use Conditions"
    description = (
        "The optional Conditions section includes statements that define when a resource is created or when a property is defined. For example, you can compare whether a value is equal to another value. Based on the result of that condition, you can conditionally create resources. If you have multiple conditions, separate them with commas."
        "\n\nTasks:\n\n"
        "- Use the previous template.yaml.\n"
        "- Add a CustomAmiId Paramater with an empty default value: ''.\n"
        "- Create a Condition UseCustomAmi.\n"
        "- Add an !If function to the ImageId.\n"
        "- Deploy the stack with a custom AMI id: ami-d834aba1"
        "- Deploy the stack with stack name: awslabs \n"
        "\nTips & Links:\n\n"
        "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/conditions-section-structure.html \n"
        "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-conditions.html \n"
    )

    def start(self):
        self.instructions()

    def validate(self):

        if os.path.isfile('./template.yaml'):
            with open('./template.yaml', 'r') as f:
                try:
                    doc = yaml.load(f, Loader=CfnYamlLoader)
                except:
                    return self.fail("Failed to load your template.yaml")
                if doc is None:
                    return self.fail("No valid yaml!")
                else:
                    try:
                        latest = doc['Parameters']['LatestAmiId']['Type']
                        custom = doc['Parameters']['CustomAmiId']['Type']
                        condition = doc['Conditions']['UseCustomAmi']
                        ami = doc['Resources']['Ec2Instance']['Properties']['ImageId']
                        click.echo('template.yaml looks valid')
                    except:
                        return self.fail("Your template.yaml contains errors.")
                    
                    # is condition ok?
                    if ( condition != ODict([('Fn::Not', [ODict([('Fn::Equals', [ODict([('Ref', 'CustomAmiId')]), ''])])])]) and
                         condition != ODict([('Fn::Not', [ODict([('Fn::Equals', ['Ref CustomAmiId', ''])])])])
                    ):
                        return self.fail("Condition is not correctly configured.")

                    # is imageId ok?
                    if ( ami != ODict([('Fn::If', ['UseCustomAmi', ODict([('Ref', 'CustomAmiId')]), ODict([('Ref', 'LatestAmiId')])])]) and 
                         ami != ODict([('Fn::If', ['UseCustomAmi', 'Ref CustomAmiId', 'Ref LatestAmiId'])])
                    ):
                        return self.fail("The If statement in ImageID is not correctly configured.")

                    # stack
                    client = boto3.client('cloudformation')
                    try:
                        stack = client.describe_stacks(
                            StackName='awslabs'
                        )
                        if stack['Stacks'][0]['Parameters'][0]['ParameterKey'] == "CustomAmiId":
                            param_ami = stack['Stacks'][0]['Parameters'][0]['ParameterValue']
                        else:
                            param_ami = stack['Stacks'][0]['Parameters'][1]['ParameterValue']
                        click.echo('found the stack!')
                    except:
                        return self.fail("Stack awslabs not deployed.")
                    
                    # resource
                    try:
                        resource = client.describe_stack_resources(
                            StackName='awslabs',
                            LogicalResourceId='Ec2Instance'
                        )
                        instance_id = resource['StackResources'][0]['PhysicalResourceId']
                        click.echo('found the resource! ({})'.format(instance_id))
                    except:
                        return self.fail("Stack does not contain a resource Ec2Instance.")
                    
                    # instance check
                    try:
                        ec2 = boto3.client('ec2')
                        instance = ec2.describe_instances(
                            InstanceIds=[instance_id]
                        )
                    except:
                        return self.fail("Cannot find the instance.")

                    if not instance['Reservations'][0]['Instances'][0]['ImageId'] == param_ami:
                        return self.fail("Deployed instance has a wrong ImageId")
                    else:
                        return self.success("You deployed the correct ami, with the correct parameter!")
        else:
            return self.fail("Cannot find template.yaml")