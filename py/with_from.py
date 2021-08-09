"""
Initializing a DataClass instance from a dict is pretty easy: You
just call Dataclass(**dict).

Unless that dict has more values than you want to import in your
dataclass. Then this will fail and complain about missing fields.

Since we're not interested in _all_ the fields, let's add a custom
from_ method that essentially does Dataclass(**dict), but only
includes those values from the dict for which the Dataclass actually
has a field.

Use:

@with_from
@dataclass
class SomeData:
    some_value: str

passed_in_from_api = {
    some_value: "one",
    other_value: "two"
}

somedata = SomeData.from_(passed_in_from_api)
assert somedata.some_value == "one"
"""

def dataclass_from_dict(Dataclass, values):
    """ Grab all the Dataclass's fields from `values` and return an instance. """
    return Dataclass(**{
        fldname: values[fldname]
        for fldname in Dataclass.__dataclass_fields__
        if fldname in values
    })

def with_from(Dataclass):
    Dataclass.from_ = lambda values: dataclass_from_dict(Dataclass, values)
    return Dataclass
