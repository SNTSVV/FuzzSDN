#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import math
from collections.abc import Iterable


class Interval:
    """
    Represents a closed interval [A, B] of numbers
    """

    # ===== ( init ) ===========================================================

    def __init__(self, *bounds):
        self._inf = None
        self._sup = None

        # Case where there is two int/float provided
        if len(bounds) >= 2:
            if all(isinstance(b, (int, float)) for b in bounds[0:2]):
                self._inf = bounds[0]
                self._sup = bounds[1]
            else:
                raise TypeError(
                    "bounds argument must contain either an iterable of "
                    "numbers, 2 number args or a single number arg, (not "
                    "'{}' and '{}')".format(type(bounds[0]).__name__,
                                            type(bounds[1]).__name__)
                )

        # Case where bounds is an iterable
        elif isinstance(bounds[0], Iterable):
            if len(bounds[0]) >= 2:
                if all(isinstance(b, (int, float)) for b in bounds[0][0:2]):
                    self._inf = bounds[0][0]
                    self._sup = bounds[0][1]
                else:
                    raise TypeError(
                        "bounds argument must contain either an iterable of "
                        "numbers, 2 number args or a single number arg, (not "
                        "'{}' and '{}')".format(type(bounds[0][0]).__name__,
                                                type(bounds[0][1]).__name__)
                    )
            elif isinstance(bounds[0][0], (int, float)):
                self._inf = self._sup = bounds[0][0]

            else:

                raise ValueError(
                    "bounds is an iterable so it should be of length 2 "
                    "(not {})".format(type(bounds[0]).__name__, len(bounds[0]))
                )

        # Case where there is a single number
        elif isinstance(bounds[0], (int, float)):
            self._inf = self._sup = bounds[0]

        else:
            raise TypeError(
                "bounds argument must contain either an iterable of numbers, "
                "2 number args or a single number arg "
                "(not '{}')".format(type(bounds).__name__)
            )

        if self._inf > self._sup:
            raise ValueError("Lower bound value '{}' is bigger than the upper"
                             "bound value '{}'.".format(self._inf, self._sup))

    # ===== ( Properties ) =====================================================

    @property
    def inf(self):
        return self._inf

    @property
    def sup(self):
        return self._sup

    @property
    def centre(self):
        return float((self._inf + self._sup)) / 2

    # ===== ( Overloads ) ======================================================

    def __repr__(self):
        return "Interval({}, {})".format(self._inf, self._sup)

    def __str__(self):
        if self.inf == self.sup:
            return "[{}]".format(self.inf)
        else:
            return "[{}, {}]".format(self.inf, self.sup)

    def __len__(self):
        return abs(self._inf - self._sup) + 1

    def __contains__(self, item):
        if isinstance(item, Interval):
            return (self.inf <= item.inf <= self.sup and
                    self.inf <= item.sup <= self.sup)

        elif isinstance(item, (int, float)):
            return self.inf <= item <= self.sup

        else:
            raise TypeError("Unsupported operation '__contains__' for: "
                            "'{}' and '{}'".format(type(self).__name__,
                                                   type(item).__name__))

    # ===== ( Setters ) ========================================================

    @inf.setter
    def inf(self, value):
        self._inf = -math.inf if value is None else value

    @sup.setter
    def sup(self, value):
        self._sup = math.inf if value is None else value

    # ===== ( Methods ) ========================================================

    def overlaps(self, other):
        return (
                (other.inf <= self.inf <= other.sup) or
                (other.inf <= self.sup <= other.sup) or
                (self.inf <= other.inf <= self.sup) or
                (self.inf <= other.sup <= self.sup)
        )

    def is_adjacent(self, other):
        return (
                (self.sup == other.inf - 1) or
                (self.inf == other.sup + 1) or
                (other.sup == self.inf - 1) or
                (other.inf == self.inf + 1)
        )

    def is_connected(self, other):
        """
        Returns ``True`` if there exists a (possibly empty) range which is
        enclosed by both this range and other.
        Examples:
        * [1, 3] and [5, 7] are not connected
        * [5, 7] and [1, 3] are not connected
        * [2, 4) and [3, 5) are connected, because both enclose [3, 4)
        * [1, 3) and [3, 5) are connected, because both enclose the empty range
          [3, 3)
        * [1, 3) and (3, 5) are not connected
        """

        return self.overlaps(other) or self.is_adjacent(other)


class Union:
    """
    Represents an Union of Intervals
    """

    # ===== ( Constructors ) ===================================================

    def __init__(self, *args):
        self._intervals = []

        for i in range(len(args)):
            # From an Interval class
            if isinstance(args[i], Interval):
                self._intervals.append(args[i])

            # From a union class
            elif isinstance(args[i], Union):
                for j in args[i].intervals:
                    self._intervals.append(j)

            #  Create an interval object (if possible) from the argument and add
            # it to the list of intervals
            else:
                self._intervals.append(Interval(args[i]))

        self._canonicalize()
    # End def __init__

    # ===== ( Properties ) =====================================================

    @property
    def intervals(self):
        return self._intervals

    # ===== ( Builtins Overloads ) =============================================

    def __repr__(self):
        """ Return repr(self). """
        repr_str = "Union("
        first = True
        for i in self._intervals:
            if first is True:
                first = False
            else:
                repr_str += ", "
            repr_str += str(i)
        repr_str += ")"
        return repr_str
    # End def __repr__

    def __str__(self):
        """ Return str(self). """
        repr_str = "["
        first = True
        for i in self._intervals:
            if first is True:
                first = False
            else:
                repr_str += ", "
            repr_str += str(i)
        repr_str += "]"
        return repr_str
    # End def __str__

    def __iter__(self):
        """ Implement iter(self). """
        for i in self._intervals:
            yield i
    # End def __iter__

    # ===== ( Operators ) ======================================================

    def union(self, other, inplace=False):
        """
        Performs an union between the Union and the Interval / Union
        :param inplace:
        :param other:
        :return:
        """
        if isinstance(other, Interval):
            return_value = Union(*self._intervals, other)

        elif isinstance(other, Union):
            return_value = Union(self, other)

        else:
            raise TypeError("Unsupported operation 'union' for: "
                            "'{}' and '{}'".format(type(self).__name__,
                                                   type(other).__name__))

        if inplace:
            self._intervals = return_value.intervals
            self._canonicalize()
        else:
            return return_value
    # End def union

    def inter(self, other, inplace=False):
        """
        Performs an intersection between the Union and the Interval / Union
        :param inplace:
        :param other:
        :return:
        """
        # [1, 4], [10] / [2, 20]
        self._canonicalize()
        intervals = list()

        if isinstance(other, Interval):
            for i in self:
                if i.overlaps(other):
                    intervals.append(
                        Interval(
                            (
                                max(i.inf, other.inf),
                                min(i.sup, other.sup)
                            )
                        )
                    )

        elif isinstance(other, Union):
            other._canonicalize()

            for i in self:
                for j in other:
                    if i.overlaps(j):
                        intervals.append(
                            Interval(
                                (
                                    max(i.inf, j.inf),
                                    min(i.sup, j.sup)
                                )
                            )
                        )
        else:
            raise TypeError("Unsupported operation 'intersection' for: "
                            "'{}' and '{}'".format(type(self).__name__,
                                                   type(other).__name__))

        if inplace:
            self._intervals = intervals
            self._canonicalize()
        else:
            return Union(*intervals)
    # End def inter

    # ===== ( Private Methods ) ================================================

    def _canonicalize(self) -> None:
        """
        Canonicalize the Union
        """
        # First sort the intervals by their inferior bound
        self._intervals.sort(key=lambda interval: interval.inf)
        # Create a new interval list and get the first item in the list
        new_ints = [self._intervals[0]] if len(self._intervals) > 0 else list()
        # Iterate through the intervals
        for current in self._intervals:
            previous = new_ints[-1]
            # if the new interval is connected with the precedent, we skip it
            if current in previous:
                continue
            # else if they are connected, we merge them
            elif current.is_connected(previous):
                previous.inf = min(previous.inf, current.inf)
                previous.sup = max(previous.sup, current.sup)
            # else, we add the current interval to the list
            else:
                new_ints.append(current)
        # Assign the new list of intervals to self._intervals
        self._intervals = new_ints
    # End def _canonicalize
# End class Union
