from operator import itemgetter as _itemgetter
from collections import OrderedDict as _OrderedDict

class OptionError(Exception):
  """ An error occured while parsing the arguments or interpreting the cmdspec"""
  def __init__(self,msg,*args):
    """Initialise the Exception"""
    self.msg=msg
    self.args=args
  def __str__(self):
    """Convert the Exception to a string"""
    if len(self.args)>0:
      return self.msg+": "+", ".join(str(a) for a in self.args)
    else:
      return self.msg

class CmdSpec(tuple):
    'A command specification'

    __slots__ = ()

    def __new__(_cls, requiredarguments=(), optionalarguments=(), repeatable=False, options=()):
        'Create a command specification'
        return tuple.__new__(_cls, (requiredarguments, optionalarguments, repeatable, options))

    def __repr__(self):
        'Return a nicely formatted representation string'
        return 'CmdSpec(requiredarguments=%r, optionalarguments=%r, repeatable=%r, options=%r)' % self

    @property
    def __dict__(self):
        'A new OrderedDict mapping field names to their values'
        return _OrderedDict(zip(self._fields, self))

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        return tuple(self)

    def __getstate__(self):
        'Exclude the OrderedDict from pickling'
        return None

    def maxarguments(self):
        'Maximum number of arguments we can take'
        if self.repeatable:
          return _sys.maxsize
        else:
          return len(self.requiredarguments)+len(self.optionalarguments)
    
    def minarguments(self):
        'Minimum number of arguments we can take'
        return len(self.requiredarguments)

    def hasarguments(self):
        'Are there any arguments'
        return len(self.requiredarguments)>0 or len(self.optionalarguments)>0
    
    def hasoptions(self):
        'Are there any arguments'
        return len(self.options)>0

    def _allarguments(self):
        'All the arguments'
        return self.requiredarguments+self.optionalarguments

    def combine(self,other):
        '''Combine another command spec with this one.
           
           Ensures that it makes sence to combine the command specifications. i.e. that the first wouldn't already absorb all the arguments'''
        if other is not None:
          if len(other.requiredarguments)>0:
            raise OptionError("Error combining arguments: Can't add more required arguments")
          if self.repeatable:
            if len(other.optionalarguments)>0:
              raise OptionError("Error combing arguments: Can't add extra arguments, already have a catch all argument")
            return CmdSpec(self.requiredaruments,self.optionalarguments,True,self.options+other.options)
          else:
            return CmdSpec(self.requiredarguments,self.optionalarguments+other.optionalarguments,other.repeatable,self.options+other.options)
        return self
 

    requiredarguments = property(_itemgetter(0), doc='The required arguments for the command')
    
    optionalarguments = property(_itemgetter(1), doc='The optional arguments for the command')

    allarguments = property(_allarguments)

    repeatable = property(_itemgetter(2), doc='Is the last argument repeatable')

    options = property(_itemgetter(3), doc='The options for the command')

class ArgSpec(tuple):
    'An argument specification'

    __slots__ = ()

    def __new__(_cls, name, description, conversion):
        'Create a new argument specifcation'
        return tuple.__new__(_cls, (name, description, conversion))

    def __repr__(self):
        'Return a nicely formatted representation string'
        return 'ArgSpec(name=%r, description=%r, conversion=%r)' % self

    @property
    def __dict__(self):
        'A new OrderedDict mapping field names to their values'
        return OrderedDict(zip(self._fields, self))

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        return tuple(self)

    def __getstate__(self):
        'Exclude the OrderedDict from pickling'
        return None

    name = property(_itemgetter(0), doc='The name of the argument')

    description = property(_itemgetter(1), doc='A description for the argument')

    conversion = property(_itemgetter(2), doc='A function to convert the value to the appropriate type')

class OptSpec(tuple):
    'An option specification'

    __slots__ = ()

    def __new__(_cls, shortforms, longforms, description, keyword, argument, value_or_conversion):
        'Create a new option specification'
        return tuple.__new__(_cls, (shortforms, longforms, description, keyword, argument, value_or_conversion))

    def __repr__(self):
        'Return a nicely formatted representation string'
        return 'OptSpec(shortforms=%r, longforms=%r, description=%r, keyword=%r, argument=%r, value_or_conversion=%r)' % self

    @property
    def __dict__(self):
        'A new OrderedDict mapping field names to their values'
        return OrderedDict(zip(self._fields, self))

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        return tuple(self)

    def __getstate__(self):
        'Exclude the OrderedDict from pickling'
        return None
    
    def hasargument(self):
        'Does this option take an argument'
        return self.argument is not None

    shortforms = property(_itemgetter(0), doc='The short option names')

    longforms = property(_itemgetter(1), doc='The long option names')

    description = property(_itemgetter(2), doc='The description of the option')

    keyword = property(_itemgetter(3), doc='The keyword to store the options result in')

    argument = property(_itemgetter(4), doc='The name of the argument to the option or None')

    value_or_conversion = property(_itemgetter(5), doc='If argument is None then the value to store if this option is given'
        ' else the function to convert the options argument to the appropriate type')

    value = property(_itemgetter(5), doc='The value to store if this option is given. Only valid if argument is None. Alias for value_or_conversion')

    conversion = property(_itemgetter(5), doc='The function to convert the options argument to the appropriate type. Only valid if argument is None. Alias for value_or_conversion')

