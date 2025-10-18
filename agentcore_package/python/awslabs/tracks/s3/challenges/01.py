from awslabs.challenge import Challenge
import boto3

class MyChallenge(Challenge):

    title = "Create an S3 Bucket"
    description = (
        "Amazon S3 has a simple web services interface that you can use to store and retrieve any amount of data, at any time, from anywhere on the web. It gives any developer access to the same highly scalable, reliable, fast, inexpensive data storage infrastructure that Amazon uses to run its own global network of web sites. The service aims to maximize benefits of scale and to pass those benefits on to developers."
        "\n\nTasks:\n\n"
        " - Create a bucket in your account. \n"
        " - Create a file readme.txt with content 'awslabs'.\n"
        " - Upload this readme.txt to the root of your bucket.\n"
        "\nTips & Links:\n\n"
        "- https://docs.aws.amazon.com/cli/latest/reference/s3/index.html \n"
    )

    def start(self):

        self.instructions()

    def validate(self):

        client = boto3.client('s3')
        buckets = client.list_buckets()
        object_found = False
        usedbucket = ""

        for bucket in buckets['Buckets']:
            try:
                obj = client.get_object(Bucket=bucket['Name'], Key='readme.txt')
                if "awslabs" in obj['Body'].read().decode('utf-8'):
                    object_found = True
                    usedbucket = bucket["Name"]
                    break
            except:
                pass

        if object_found:
            self.save('bucket', usedbucket)
            return self.success("You created a bucket {}, uploaded a file with the correct content.".format(usedbucket))
        else:
            return self.fail("Cannot find a bucket containing a readme.txt with 'awslabs' in it. It should not contain any spaces, new lines etc.")
        
