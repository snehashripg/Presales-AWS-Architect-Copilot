from awslabs.challenge import Challenge
import boto3

class MyChallenge(Challenge):
    title = "A Static Website with S3"
    description = (
        "Amazon S3 has a simple web services interface that you can use to store and retrieve any amount of data, at any time, from anywhere on the web. It gives any developer access to the same highly scalable, reliable, fast, inexpensive data storage infrastructure that Amazon uses to run its own global network of web sites. The service aims to maximize benefits of scale and to pass those benefits on to developers."
        "\n\nTasks:\n\n"
        " - Change the bucket into a website \n"
        " - Add an index.html.\n"
        "\nTips & Links:\n\n"
        "https://docs.aws.amazon.com/cli/latest/reference/s3/website.html \n"
    )

    def start(self):
        self.instructions()

    def validate(self):

        client = boto3.client('s3')

        bucket_is_website = False
        response = client.get_bucket_website(
                Bucket=self.get('bucket')
            )
        print(response['IndexDocument']['Suffix'])
        try:
            response = client.get_bucket_website(
                Bucket=self.get('bucket')
            )
            if 'IndexDocument' in response and response['IndexDocument']['Suffix'] == 'index.html':
                bucket_is_website = True
        except:
            pass

        if bucket_is_website:
            return self.success("The bucket is indeed a website. Good job!")
        else:
            return self.fail("The bucket {} is NOT a website and NOT serving an index.html containing hello world. Try again.".format(self.get('bucket')))
