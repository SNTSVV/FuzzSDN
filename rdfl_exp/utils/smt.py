from z3 import Z3Exception, Z3_UNINTERPRETED_SORT, is_array, z3


def get_z3_model(formula, n):
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
    return result


# Return True if a z3 formula has exactly one model.
def has_exactly_z3_one_model(formula):
    return len(get_z3_model(formula, 2)) == 1
