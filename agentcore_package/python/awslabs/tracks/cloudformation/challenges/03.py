from awslabs.challenge import Challenge
import boto3
import os
import yaml
import click
from cfn_tools.yaml_loader import CfnYamlLoader, ODict

class MyChallenge(Challenge):

    title = "Mappings"
    description = (
        "The optional Mappings section matches a key to a corresponding set of named values. For example, if you want to set values based on a region, you can create a mapping that uses the region name as a key and contains the values you want to specify for each specific region. You use the Fn::FindInMap intrinsic function to retrieve values in a map."
        "\n\nTasks:\n\n"
        "- Change the instance type to t2.micro.\n"
        "- Now create a mapping AMIs.\n"
        "- Top level key: eu-west-1, etc...\n"
        "- Second level key: AMI\n"
        "- The eu-west-1 AMI = ami-d834aba1\n"
        "- Deploy the stack with stack name: awslabs \n"
        "\nTips & Links:\n\n"
        "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/mappings-section-structure.html \n"
        "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-findinmap.html \n"
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
                        it = doc['Mappings']['AMIs']['eu-west-1']['AMI']
                        it = doc['Resources']['Ec2Instance']['Properties']['InstanceType']
                        ami = doc['Resources']['Ec2Instance']['Properties']['ImageId']
                        click.echo('template.yaml looks valid')
                    except:
                        return self.fail("Your template.yaml contains errors.")
                    
                    if it != 't2.micro':
                        return self.fail("InstanceType is not t2.micro")  
                    elif ami != ODict([('Fn::FindInMap', ['AMIs', 'eu-west-1', 'AMI'])]):
                        return self.fail("ImageId has not a correct !FindInMap function")  
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
