# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

""" A ripoff^w basic implementation of AngularJS's scopes and dependency injection pattern """

import random

class AbstractStep(object):
    def step(self):
        raise NotImplemented

    def __call__(self, scope):
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


def main():
    scope = {}

    pipeline = [
        ChooseRandomGreeting(),
        ChooseRandomName(),
        FormatGreeting(),
        RandomCase(),
        Greet()
    ]

    for step in pipeline:
        step(scope)


if __name__ == '__main__':
    main()
