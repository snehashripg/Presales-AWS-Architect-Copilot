import boto3
import importlib
import configparser
import os
import click
from awslabs.challenge import Challenge
from awslabs.betterguid import BetterGuid


def load_class(full_class_string):
    """
    dynamically load a class from a string
    """

    class_data = full_class_string.split(".")
    module_path = ".".join(class_data[:-1])
    class_str = class_data[-1]

    module = importlib.import_module(module_path)
    # Finally, we retrieve the Class
    return getattr(module, class_str)


def challenge_id(var):
    var = str(var)
    return '{0}'.format(var.zfill(2))


def load_challenge(track_id, track_name, challenge_id) -> Challenge:
    clazz = load_class('awslabs.tracks.{}.challenges.{}.MyChallenge'.format(track_id, challenge_id))
    return clazz(track_id, track_name)

class Track(object):

    id = ''
    name = ''
    description = ''

    def __init__(self, id):
        ''' test '''
        self.id = id

    def start(self):
        if self.get('current') is '0' or self.get('current') is '':
            click.echo(click.style("\n# Track: {}\n".format(self.name), fg='red', bold=True))
            click.echo(self.description)
            challenge = load_challenge(self.id, self.name, '01')
            challenge.start()
            self.save('current', 1)
            self.save('session', BetterGuid().new_guid())
        else:
            click.echo("Track is in progress, Type `awslabs {0}` to validate your current challenge ")
            click.echo("or `awslabs {0} stop` to stop the track.".format(self.id))

    def help(self):
        challenge = load_challenge(self.id,
                                   self.name,
                                   challenge_id(self.get('current')))
        challenge.start()

    def validate(self):
        self._go()

    def _go(self):
        try:
            challenge = load_challenge(self.id,
                                       self.name,
                                       challenge_id(self.get('current')))
        except:
            click.echo("Sorry, no next challenge found for {}. Have you completed this track?".format(self.id))
            exit()
        # if validate was OK, then load the next challenge start
        if challenge.check():
            self.save('current', int(self.get('current'))+1)
            try:
                challenge = load_challenge(self.id,
                                           self.name,
                                           challenge_id(int(self.get('current'))))
                challenge.start()
            except:
                # if there is no next challenge, you're finished!
                click.echo(click.style("\n\nCongratulations!! You have completed the track: {}\n\n".format(self.name), fg='green'))


    def save(self, key, value):
        file = '~/.awslabs/config'
        filename = os.path.expanduser(file)
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        config = configparser.ConfigParser()
        config.read(filename)

        # if section does not exist
        if not config.has_section(self.id):
            config.add_section(self.id)

        # add the key and write the file
        config.set(self.id, key, str(value))
        with open(filename, 'w') as fp:
            config.write(fp)

    def get(self, key, default = ''):
        file = '~/.awslabs/config'
        filename = os.path.expanduser(file)
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        config = configparser.ConfigParser()
        config.read(filename)
        if self.id in config.sections():
            if key in config[self.id]:
                return config[self.id][key]
            else:
                return default
        else:
            return default

    def delete(self):
        file = '~/.awslabs/config'
        filename = os.path.expanduser(file)
        config = configparser.ConfigParser()
        config.read(filename)
        config.remove_section(self.id)
        with open(filename, 'w') as fp:
            config.write(fp)

    def stop(self):
        command = click.style("awslabs {} start".format(self.name), bold=True)
        print("Track {} is now stopped. To restart, type: {}".format(self.name, command))
        self.delete()

    def restart(self):
        click.echo("Progress in track {} is deleted. Restarting...".format(self.name))
        self.delete()
        self.start()
