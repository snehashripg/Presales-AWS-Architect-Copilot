import boto3
from awslabs.challenge import Challenge

class MyChallenge(Challenge):
    """
    You can use a NAT gateway to enable instances in a private subnet to
    connect to the Internet or other AWS services, but prevent the Internet
    from initiating connections with the instances. Since the public
    subnets have internet access, the NAT gateways have to be deployed in
    the public subnets.

    Tasks:
    - Place a NAT gateway in each of the two public subnets.

    Tips & Links:
    - CloudFormation documentation:
      https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-natgateway.html
    """

    title = "NAT Gateways"
    description = __doc__

    def validate(self):
        client = boto3.client("ec2")
        vpc_id = self.get("vpc_id")

        subnet_ids = [self.get("subnet_id1"), self.get("subnet_id2")]

        nat_gateways = [nat_gateway(client, vpc_id, subnet_id) for subnet_id in subnet_ids]

        if None in nat_gateways:
            self.fail("Could not find the NAT gateways associated with the public subnets.")

        self.save("nat_gateway_id1", nat_gateways[0]["NatGatewayId"])
        self.save("nat_gateway_id2", nat_gateways[1]["NatGatewayId"])

        self.success("You created a VPC, internet gateway, subnets and NAT gateways.")


def nat_gateway(client, vpc_id, subnet_id):
    ngws = client.describe_nat_gateways()["NatGateways"]
    for ngw in ngws:
        if ngw["State"] == "available" and ngw["VpcId"] == vpc_id and ngw["SubnetId"] == subnet_id:
            return ngw
