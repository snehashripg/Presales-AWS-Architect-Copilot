import boto3
from awslabs.challenge import Challenge


class MyChallenge(Challenge):
    """
    A route table contains a set of rules, called routes, that are used to
    determine where network traffic is directed. You can make a subnet a public
    subnet by adding a route to an Internet gateway. To enable instances in a
    private subnet to connect to the Internet, you can add a route to a
    NAT gateway in one of the public subnets.

    Tasks:
    - Create one route table for both public subnets.
    - Add a default route (0.0.0.0/0) to internet gateway to the public route table.
    - Create one route table per private subnet (total 2).
    - Add a default route to the NAT Gateway of that AZ.

    Tips & Links:
    - IPv4 explained: https://en.wikipedia.org/wiki/IP_address
    - CloudFormation documentation:
      https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-route-table.html
      https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-route.html
    """

    title = "Route Tables"
    description = __doc__

    def validate(self):
        client = boto3.client("ec2")
        vpc_id = self.get("vpc_id")
        igw_id = self.get("igw_id")
        ngw_id1 = self.get("nat_gateway_id1")
        ngw_id2 = self.get("nat_gateway_id2")

        subnet_ids = [self.get("subnet_id{}".format(i)) for i in [1, 2, 3, 4]]

        route_tables = [route_table(client, vpc_id, subnet_id) for subnet_id in subnet_ids]

        if None in route_tables:
            self.fail("Could not find all route tables. Are the route tables associated to their respective subnets?")

        if not igw_id in [r.get("GatewayId") for r in route_tables[0]["Routes"]]:
            self.fail("Internet gateway is not coupled to the route table for the public subnets")

        if not igw_id in [r.get("GatewayId") for r in route_tables[1]["Routes"]]:
            self.fail("Internet gateway is not coupled to the route table for the public subnets")

        if not ngw_id1 in [r.get("NatGatewayId") for r in route_tables[2]["Routes"]]:
            self.fail("Internet gateway is not coupled to the route table for the private subnets")

        if not ngw_id2 in [r.get("NatGatewayId") for r in route_tables[3]["Routes"]]:
            self.fail("Internet gateway is not coupled to the route table for the private subnets")

        self.success("Well done. You have configured a usable VPC.")


def route_table(client, vpc_id, subnet_id):
    rts = client.describe_route_tables()["RouteTables"]
    for rt in rts:
        if rt["VpcId"] == vpc_id and subnet_id in [a.get("SubnetId") for a in rt["Associations"]]:
            return rt

