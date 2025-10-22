from awslabs.challenge import Challenge
import boto3
import os
import click

class MyChallenge(Challenge):
    """
    NACL

    AWS uses a layered security model. We already gain a lot by running
    services that do not need to be internet facting our private subnet.
    We can secure this even more by adding Network Access Control Lists
    (NACL's for short) to our configuration.

    It's well worth noting that Network ACL's are stateless. This means
    that an incoming packet (e.g. a HTTP request over port 80) and the
    return packets (e.g. the HTTP reponse, sent to a custom port) are
    not related.

    Tasks:
    - Create one NACL table for both public subnets.
    - Add ingress  and egress rules for HTTP ((0.0.0.0/0), port 80, TCP).
    - Add ingress and egress rules for ephemeral ports (32768-65535, TCP).
    - Add a Deny for all inbound traffic that is not already handled by a preceding rule.

    Tips & Links:
    - More on Network ACL's: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
    - CloudFormation documentation:
      https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-network-acl.html
      https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-network-acl-entry.html
      https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-subnet-network-acl-assoc.html
    """

    title = "Network ACL's"
    description = __doc__

    def start(self):
        self.instructions()

    def validate(self):
        client = boto3.client("ec2")
        vpc_id = self.get("vpc_id")
        subnet_id1 = self.get("subnet_id1")
        subnet_id2 = self.get("subnet_id2")

        nacl = network_acl(client, vpc_id, subnet_id1)

        nacl_subnet_ids = [n["SubnetId"] for n in nacl["Associations"]]
        if subnet_id2 not in nacl_subnet_ids:
            self.fail("Both public networks should be attached to the same NACL")

        nacl_entries = nacl["Entries"]
        ingress = [e for e in nacl_entries if not e["Egress"]]
        egress = [e for e in nacl_entries if e["Egress"]]

        if len(ingress) != 3:
            self.fail("The NACL should contain 3 ingress rules. 2 defined by you and 1 default deny rule.")
        if len(egress) != 3:
            self.fail("The NACL should contain 3 egress rules. 2 defined by you and 1 default deny rule.")

        for e in nacl_entries:
            if e["CidrBlock"] != "0.0.0.0/0":
                self.fail("Expected CIDR block for all NACL's to be 0.0.0.0/0.")

        if not nacl_entry(ingress, "allow", 80, 80):
            self.fail("One ingress NACL should allow port 80.")
        if not nacl_entry(ingress, "allow", 32768, 65535):
            self.fail("One ingress NACL should allow ephemeral ports 32768-65535.")
        if not nacl_entry(egress, "allow", 80, 80):
            self.fail("One egress NACL should allow port 80.")
        if not nacl_entry(egress, "allow", 32768, 65535):
            self.fail("One egress NACL should allow ephemeral ports 32768-65535.")

        self.success("Almost there. Let's deploy a workload in the next step.")


def network_acl(client, vpc_id, subnet_id):
    nacls = client.describe_network_acls()["NetworkAcls"]
    for nacl in nacls:
        if vpc_id == nacl["VpcId"] and subnet_id in (n["SubnetId"] for n in nacl["Associations"]):
            return nacl


def nacl_entry(entries, action, from_port, to_port):
    try:
        return [e for e in entries if e["RuleAction"] == action \
            and e["PortRange"]["From"] == from_port \
            and e["PortRange"]["To"] == to_port][0]
    except IndexError:
        return None
