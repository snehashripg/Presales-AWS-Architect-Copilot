from awslabs.challenge import Challenge
import boto3
import os
import yaml
import click
from cfn_tools.yaml_loader import CfnYamlLoader, ODict

class MyChallenge(Challenge):

    title = "Using Parameters"
    description = (
        "Use the optional Parameters section to customize your templates. Parameters enable you to input custom values to your template each time you create or update a stack."
        "\n\nTasks:\n\n"
        " - Create a parameter AmiId to specify the id of the ami for the instance.\n"
        " - Use this AmiId: ami-d834aba1\n"
        " - Deploy in eu-west-1 \n"
        "- Deploy the stack with stack name: awslabs \n"
        "\nTips & Links:\n\n"
        "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html\n"
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
                        param_type = doc['Parameters']['AmiId']['Type']
                        it = doc['Resources']['Ec2Instance']['Properties']['InstanceType']
                        ami = doc['Resources']['Ec2Instance']['Properties']['ImageId']
                        click.echo('template.yaml looks valid')
                    except:
                        return self.fail("Your template.yaml contains errors.")

                    if it != 't2.small':
                        return self.fail("InstanceType is not t2.small and/or ImageId has no !Ref function")  
                    elif ami != ODict([('Fn::Ref:', 'AmiId')]) and ami != ODict([('Ref', 'AmiId')]):
                        return self.fail("ImageId has no !Ref function")  
                    else:
                        # stack
                        client = boto3.client('cloudformation')
                        try:
                            stack = client.describe_stacks(
                                StackName='awslabs'
                            )
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
                            click.echo('found the resource!')
                        except:
                            return self.fail("Stack does not contain a resource Ec2Instance.")
                        
                        # instance check
                        try:
                            ec2 = boto3.client('ec2')
                            instance = ec2.describe_instances(
                                InstanceIds=[instance_id]
                            )
                            click.echo('found the instance!')
                        except:
                            return self.fail("Cannot find the instance.")

                        if not instance['Reservations'][0]['Instances'][0]['ImageId'] == 'ami-d834aba1':
                            return self.fail("Deployed instance has a wrong ImageId")
                        else:
                            return self.success("You deployed the correct ami, with the correct parameter!")
        else:
            return self.fail("Cannot find template.yaml")