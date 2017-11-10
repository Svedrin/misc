# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

""" A ripoff^w basic implementation of AngularJS's scopes and dependency injection pattern """

import random

class StepLibrary(type):
    """ Meta class that keeps a library of defined steps. """
    steps = {}

    def __init__( cls, name, bases, attrs ):
        type.__init__( cls, name, bases, attrs )
        if not name.startswith("Abstract"):
            StepLibrary.steps[ name ] = cls


class AbstractStep(object):
    __metaclass__ = StepLibrary

    def step(self):
        raise NotImplemented

    def run(self, scope):
        step_argdef = self.step.__code__.co_varnames
        step_argval = [scope[arg] for arg in step_argdef[2:]]
        return self.step(scope, *step_argval)


class ChooseRandomGreeting(AbstractStep):
    def step(self, scope):
        scope["greeting"] = random.choice(["Hello", "Hai", "Yo", "omg it's"])


class ChooseRandomName(AbstractStep):
    def step(self, scope):
        scope["name"] = random.choice(["John", "Steve", "Mary", "Gordy"])


class FormatGreeting(AbstractStep):
    def step(self, scope, greeting, name):
        scope["formatted_greeting"] = "%s %s!" % (greeting, name)


class RandomCase(AbstractStep):
    def step(self, scope, formatted_greeting):
        scope["formatted_greeting"] = random.choice([
            formatted_greeting,
            formatted_greeting.upper(),
            formatted_greeting.lower(),
        ])


class Greet(AbstractStep):
    def step(self, scope, formatted_greeting):
        print formatted_greeting


def run_script(stepscript):
    scope = {}

    pipeline = eval(stepscript,  {'__builtins__': None}, StepLibrary.steps)

    for step in pipeline:
        step.run(scope)


def main():
    stepscript = """[
        # Here some preparations
        ChooseRandomGreeting(),
        ChooseRandomName(),

        # Now we will do awesome things
        FormatGreeting(),
        RandomCase(),
        Greet()
    ]"""

    run_script(stepscript)


if __name__ == '__main__':
    main()
