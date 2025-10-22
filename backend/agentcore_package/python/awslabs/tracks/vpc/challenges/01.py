import boto3
from awslabs.challenge import Challenge


class MyChallenge(Challenge):
    """
    Amazon Virtual Private Cloud (Amazon VPC) enables you to launch AWS
    resources into a virtual network that you've defined. This virtual
    network closely resembles a traditional network that you'd operate
    in your own data center, with the benefits of using the scalable
    infrastructure of AWS.

    Thoughtout this challenge, use CloudFormation to provision your AWS
    account!

    Tasks:
    - Create a basic VPC and name it `awslabs`.
    - Use CIDR Block: 10.0.0.0/16.
    - Add and attach an Internet Gateway to the VPC.

    Tips & Links:
    - Getting started with VPC:
      https://aws.amazon.com/vpc/
    - CloudFormation documentation:
      https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-vpc.html
      https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-vpc-gateway-attachment.html
    """

    title = "The most basic VPC configuration"
    description = __doc__

    def validate(self):
        client = boto3.client('ec2')

        vpc = vpc_with_name(client, "awslabs")

        if not vpc:
            self.fail("No VPC with name 'awslabs' was found. (Hint: provide the name as a tag.)")

        if vpc["CidrBlockAssociationSet"][0]["CidrBlock"] != "10.0.0.0/16":
            self.fail("You have a VPC, but it's missing the right subnet (10.0.0.0/16).")

        igw = internet_gateway(client, vpc)
        if not igw:
            self.fail("No Internet Gateway is connected to your VPC.")

        self.save("vpc_id", vpc["VpcId"])
        self.save("igw_id", igw["InternetGatewayId"])

        self.success("You created a VPC with internet gateway.")


def internet_gateway(client, vpc):
    vpc_id = vpc["VpcId"]
    igws = client.describe_internet_gateways()["InternetGateways"]
    for igw in igws:
        if igw["Attachments"][0]["VpcId"] == vpc_id:
            return igw


def vpc_with_name(client, name):
    vpcs = client.describe_vpcs()["Vpcs"]
    return find_by_tags(vpcs, Name="awslabs")


def find_by_tags(items, **kwargs):
    for item in items:
        if kwargs.items() <= tags(item):
            return item


def tags(item):
    tags = {}
    for tag in item.get("Tags", []):
        tags[tag["Key"]] = tag["Value"]
    return tags.items()
