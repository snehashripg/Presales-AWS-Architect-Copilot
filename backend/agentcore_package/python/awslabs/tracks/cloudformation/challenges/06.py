from awslabs.challenge import Challenge
import boto3
import os
import yaml
import click
from cfn_tools.yaml_loader import CfnYamlLoader, ODict


class MyChallenge(Challenge):

    title = "Ref Resources, Fn::GetAtt, and Outputs"
    description = (
        "Now it's time to double the resources. We're creating a Security Group. A Security Group is a firewall which you can add to your instance. So that's what we are going to do here."
        "\n\nTasks:\n\n"
        "- Use the previous template.yaml.\n"
        "- Add a Security Group resource.\n"
        "- Use Logic ID: SecurityGroup.\n"
        "- Use for SG Description: AWSLabsInstances.\n"
        "- Use the SecurityGroups property on Instances to reference the SG.\n"
        "- Output SecurityGroupId with Logic ID SecurityGroupId.\n"
        "- Deploy the stack with stack name: awslabs \n"
        "\nTips & Links:\n\n"
        "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ec2-security-group.html \n"
        "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-getatt.html \n"
        "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html \n"
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
                        ami = doc['Resources']['Ec2Instance']['Properties']['ImageId']
                        output = doc['Outputs']['SecurityGroupId']['Value']
                        sg = doc['Resources']['Ec2Instance']['Properties']['SecurityGroups'][0]
                        gd = doc['Resources']['SecurityGroup']['Properties']['GroupDescription']
                        click.echo('template.yaml looks valid')
                    except:
                        return self.fail("Your template.yaml is not configured correctly. Fix it and try again.")
                    
                    if sg != ODict([('Fn::Ref:', 'SecurityGroup')]) and sg != ODict([('Ref', 'SecurityGroup')]):
                        return self.fail("Use Ref to use ref the SecurityGroup")
                    elif output != ODict([('Fn::GetAtt', ['SecurityGroup', 'GroupId'])]):
                        return self.fail("Ouptut has no correct GetAtt function")
                    else:
                        # stack
                        client = boto3.client('cloudformation')
                        try:
                            stack = client.describe_stacks(
                                StackName='awslabs'
                            )
                            cfn_output_sg = stack['Stacks'][0]['Outputs'][0]['OutputValue']
                            click.echo('found the stack!')
                        except:
                            return self.fail("Stack awslabs is not deployed, still updating or incorrect.")

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
                            instance_sg_id = instance['Reservations'][0]['Instances'][0]['SecurityGroups'][0]['GroupId']
                        except:
                            return self.fail("Cannot find the instance.")

                        # does the instance have the right sg
                        if instance_sg_id != cfn_output_sg:
                            return self.fail("Deployed instance has a wrong SecurityGroupId")
                        else:
                            return self.success("Stack has been deployed, with the correct SecurityGroup!")
        else:
            return self.fail("Cannot find template.yaml")