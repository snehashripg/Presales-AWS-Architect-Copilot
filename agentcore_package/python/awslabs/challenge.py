import click
import configparser
import os

class UnfinishedChallengeException(Exception):
    """
    Raise `UnfinishedChallengeException` when validating a challenge and the challenge is missing
    """
    def __init__(self,message):
        super(UnfinishedChallengeException,self).__init__()
        self.message = message

class Challenge(object):

    title = 't.b.d.'
    description = 't.b.d.'

    def __init__(self, track_id, track_name):
        self.track_name = track_name
        self.track_id = track_id

    def help(self) -> None:
        self.instructions()

    def start(self) -> None:
        self.instructions()

    def instructions(self) -> None:
        """ Prints the instructions of a challenge """
        click.echo(click.style("\n> Challenge: {}\n".format(self.title), fg='blue', bold=True))
        click.echo(self.description)
        command = click.style("awslabs {}".format(self.track_id), bold=True)
        click.echo("When finished type: `{}` to validate your progress.\n\n".format(command))

    def fail(self, description) -> None:
        raise UnfinishedChallengeException(description)

    def success(self, description: str) -> bool:
        """ Prints the SUCCESS message and returns True """
        click.echo(click.style("\n{}\n".format("CHALLENGE SUCCESS"), fg='green'))
        click.echo(description)
        return True

    def save(self, key: str, value: object) -> None:
        """ Save a value to the config file of this Track """
        file = '~/.awslabs/config'
        filename = os.path.expanduser(file)
        config = configparser.ConfigParser()
        config.read(filename)
        config.set(self.track_id, key, value)
        with open(filename, 'w') as fp:
            config.write(fp)

    def get(self, key: str) -> object:
        """ Get a value from the config file of this Track """
        file = '~/.awslabs/config'
        filename = os.path.expanduser(file)
        config = configparser.ConfigParser()
        config.read(filename)
        return config[self.track_id][key]

    def debug(self, text: str) -> None:
        if os.environ["AWSLABS_VERBOSE"] == "1":
            click.echo("INFO: {}".format(text))

    def validate(self) -> None:
        return self.fail("no validation implemented")

    def check(self) -> bool:
        try:
            result = self.validate()
            return result is None or result
        except UnfinishedChallengeException as e:
            click.echo(click.style("\n{}\n".format("CHALLENGE FAILED"), fg='red'))
            click.echo("  {}\n".format(e.message))
            click.echo("{}\n".format("Try again!"))
            return False
