import boto3
from awslabs.challenge import Challenge


class MyChallenge(Challenge):
    """
    Add 4 subnets to the VPC created in the previous exercise.

    If a subnet's traffic is routed to an internet gateway, the subnet is known as a public subnet.

    Tasks:
    - Add 4 subnets and update the stack.
      - Two Public Subnets (10.0.0.0/24 and 10.0.1.0/24).
      - Two Private Subnets (10.0.2.0/24 and 10.0.3.0/24).
    - Separate the Subnets in 2 AZs.
    - Associate the subnets to the VPC.

    Tips & Links:
    - CloudFormation documentation:
      https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-subnet.html

    """
    title = "Basic VPC with subnets"
    description = __doc__

    cidrs = [
        "10.0.0.0/24", "10.0.1.0/24",
        "10.0.2.0/24", "10.0.3.0/24"
    ]

    def validate(self):
        client = boto3.client("ec2")
        vpc_id = self.get("vpc_id")

        subnets = [subnet(client, vpc_id, cidr) for cidr in self.cidrs]

        if None in subnets:
            self.fail("You have a VPC, but you're missing at least one subnet. Did you associate the subnets to your VPC?")

        if subnets[0]["AvailabilityZone"] == subnets[1]["AvailabilityZone"]:
            self.fail("Your public subnets are deployed in the same availability zone.")

        if subnets[2]["AvailabilityZone"] == subnets[3]["AvailabilityZone"]:
            self.fail("Your private subnets are deployed in the same availability zone.")

        self.save("subnet_id1", subnets[0]["SubnetId"])
        self.save("subnet_id2", subnets[1]["SubnetId"])
        self.save("subnet_id3", subnets[2]["SubnetId"])
        self.save("subnet_id4", subnets[3]["SubnetId"])

        self.success("You created a VPC with internet gateway and added subnets.")


def subnet(client, vpc_id, cidr):
    subnets = client.describe_subnets()["Subnets"]
    for subnet in subnets:
        if subnet["VpcId"] == vpc_id and subnet["CidrBlock"] == cidr:
            return subnet

