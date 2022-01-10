from random import choice

from z3 import Z3Exception, Z3_UNINTERPRETED_SORT, is_array, z3


def get_model(formula, n, exact=False):
    """
    Generate n models for a z3 formula
    :param formula: the z3 formula to generate models for
    :param n:  the numbe of models to generate
    :param exact: if set to true, duplicate some entries to get the exact number of models
    :return: a tuple of exactly n models if exact is true or at max n models
    """
    result = []
    s = z3.Solver()
    s.add(formula)
    while len(result) < n and s.check() == z3.sat:
        m = s.model()
        result.append(m)
        # Create a new constraint the blocks the current model
        block = []
        for d in m:
            # d is a declaration
            if d.arity() > 0:
                raise Z3Exception("uninterpreted functions are not supported")
            # create a constant from declaration
            c = d()
            if is_array(c) or c.sort().kind() == Z3_UNINTERPRETED_SORT:
                raise Z3Exception("arrays and uninterpreted sorts are not supported")
            block.append(c != m[d])
        s.add(z3.Or(block))

    # If the exact number of sample is requested and less models than requested where generated, then duplicate some of
    # the entries and append them to the results.
    if len(result) < n and exact is True:
        result.extend(choice(result) for _ in range(n - len(result)))  # n-len(result) = number of missing models

    return result
# End def get_z3_model


# Return True if a z3 formula has exactly one model.
def has_exactly_one_model(formula):
    return len(get_model(formula, 2)) == 1
# End def has_exactly_one_model
