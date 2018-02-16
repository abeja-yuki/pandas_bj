from typing import Any, Hashable, Callable, Union, List
from abc import ABCMeta, abstractmethod
import pandas
from pandas import DataFrame


class CustomColumn(metaclass=ABCMeta):
    @abstractmethod
    def __call__(self, df: pandas.DataFrame) -> pandas.Series:
        pass

    @abstractmethod
    def column_check(self, columns: List[Any]) -> bool:
        pass


class Range():
    def __init__(self, range_from: Any, range_to: Any,
                 from_opened: bool = False, to_opened: bool = False):
        self.range_from = range_from if not pandas.isnull(range_from) else None
        self.range_to = range_to if not pandas.isnull(range_to) else None
        self.from_opened = from_opened
        self.to_opened = to_opened

    def __str__(self):
        return f"""{'('if self.from_opened else "["}{self.range_from}, {self.range_to}{')'if self.to_opened else "]"}"""

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash((self.range_from, self.range_to, self.from_opened, self.to_opened))

    def _get_from_comp_func(self) -> Callable[[Any], bool]:
        """
        | get comparing function for range_from.
        :return: function
        """
        if self.range_from is None:
            return lambda v: True
        if self.from_opened:
            return self.range_from.__lt__
        return self.range_from.__le__

    def _get_to_comp_func(self) -> Callable[[Any], bool]:
        """
        | get comparing function for range_to.
        :return: function
        """
        if self.range_to is None:
            return lambda v: True
        if self.to_opened:
            return self.range_to.__gt__
        return self.range_to.__ge__

    def __comp_f__(self, other: 'Range'):
        # -inf:x < ???
        if self.range_from is None:
            # -inf:x < -inf:x
            if other.range_from is None:
                return None
            # -inf:x < x:x
            else:
                return True
        # x:x < -inf:x
        if other.range_from is None:
            return False
        # xf < yf
        if self.range_from < other.range_from:
            return True
        # xf > yf
        if self.range_from > other.range_from:
            return False
        # xf == yf
        # y open
        if other.from_opened and not self.from_opened:
            return True
        # x open
        if self.from_opened and not other.from_opened:
            return False
        return None

    def __comp_t__(self, other: 'Range'):
        # x:inf > ???
        if self.range_to is None:
            # x:inf > x:inf
            if other.range_to is None:
                return None
            # x:inf > x:x
            else:
                return True
        # x:x > x:inf
        if other.range_to is None:
            return False
        # xt > yt
        if self.range_to > other.range_to:
            return True
        # xt < yt
        if self.range_to < other.range_to:
            return False
        # xt == yt
        # y open
        if other.to_opened and not self.to_opened:
            return True
        # x open
        if self.to_opened and not other.to_opened:
            return False
        return None

    def __lt__(self, other: Union[Any, 'Range']):
        if isinstance(other, Range):
            if self == other:
                return False
            cf = self.__comp_f__(other)
            if cf is not None:
                return cf
            ct = self.__comp_t__(other)
            if ct is not None:
                return not ct
            return False
        return not self._get_to_comp_func()(other)

    def __gt__(self, other: Union[Any, 'Range']):
        if isinstance(other, Range):
            if self == other:
                return False
            ct = self.__comp_t__(other)
            if ct is not None:
                return ct
            cf = self.__comp_f__(other)
            if cf is not None:
                return not cf
            return False
        return not self._get_from_comp_func()(other)

    def __eq__(self, other: Union[Any, 'Range']):
        """
        | Check other is satisfy an inequality 'range_from <(=) other <(=) range_to'.
        :param other: some comparable value.
        :return: comparison result.
        """
        if isinstance(other, Range):
            return hash(self) == hash(other)
        return self._get_from_comp_func()(other) and self._get_to_comp_func()(other)

    def __ne__(self, other: Union[Any, 'Range']):
        """
        | Check __eq__ returns False or not with other value.
        :param other: other value
        :return: negative of __eq__
        """
        return not self == other


class Between(CustomColumn):
    '''
    Between class provides comparison feature with ranges.
    - Compare ranges
    - Compare range and value

    It is useful to sort to reduce computation cost.

    Between class can be used with column names in pandas.DataFrame.
    If pandas.DataFrame has columns a, b and c and you want to do like `BETWEEN a and b`,
    then you can do

    ```
    Between('a', 'b')
    ```

    If you don't want to include edge values like `2` and `5` for `BETWEEN 2 and 5`,
    you can do:

    ```
    Between('a', 'b', f_open=True and t_open=True)
    ```

    If `f_open=True`, `BETWEEN 2 and 5` doesn't contain `2` but it contains `2.0001`.

    If the column that is specified as `f` contains `NaN`, it'll considered as `-inf`.
    Conversely, `NaN` in `t` column, it'll considered as `+inf`.
    And no differences between `NaN` and `f_open` and `t_open` because infinite don't have end originally.

    '''

    def __init__(self, f: Hashable, t: Hashable, f_open: bool = False, t_open: bool = False):
        self.f = f
        self.t = t
        self.f_open = f_open
        self.t_open = t_open

    def __call__(self, df: DataFrame) -> pandas.Series:
        '''
        This function is used in `pandas_bj.merge` internally.
        It create series of `Range` from pandas.DataFrame.

        if `f` and `t` are not in it, then KeyError will raise.

        :param df: pandas.DataFrame
        :return: pandas.Series of `Range`.
        '''
        if self.f not in df.columns:
            raise KeyError(self.f)
        if self.t not in df.columns:
            raise KeyError(self.t)

        return df[[self.f, self.t]].apply(lambda v: Range(v[self.f], v[self.t], self.f_open, self.t_open), axis=1)

    def column_check(self, columns: List[Any]) -> bool:
        if self.f not in columns:
            return False
        if self.t not in columns:
            return False
        return True
