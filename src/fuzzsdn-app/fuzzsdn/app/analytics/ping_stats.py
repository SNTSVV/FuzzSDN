import re
from copy import copy
from typing import Optional, cast

RGX_DST         = r'(?<=PING\s)(?P<dst>[^\s]+)'            # Match the destination
RGX_SENT_PKT    = r'(?P<count>\d+)\spackets\stransmitted'  #
RGX_RECV_PKT    = r'(?P<count>\d+)\sreceived'              #
RGX_RTT = r'rtt.*\s?=\s?' \
          r'(?P<min>[+-]?(?:[0-9]*[.])?[0-9]+)\/' \
          r'(?P<avg>[+-]?(?:[0-9]*[.])?[0-9]+)\/' \
          r'(?P<max>[+-]?(?:[0-9]*[.])?[0-9]+)\/' \
          r'(?P<mdev>[+-]?(?:[0-9]*[.])?[0-9]+)' \
          r'\s*ms'


class PingStats:
    """
    PingStats holds information of a ping response trace after parsing it.
    """

    def __init__(self, ping_msg=None) -> None:
        self.__destination    = None
        self.__pkt_sent       = None
        self.__pkt_recv       = None
        self.__pkt_lost       = None
        self.__rtt_min        = None
        self.__rtt_max        = None
        self.__rtt_avg        = None
        self.__rtt_mdev       = None
        self.__pkt_dupe       = None

        if ping_msg is not None:
            self.parse(ping_msg)
    # End def __init__

    # ===== ( Properties ) =============================================================================================

    @property
    def destination(self) -> str:
        """
        The ping destination.
        :return: destination as str
        """
        return copy(self.__destination) if self.__destination is not None else None
    # End property destination

    @property
    def pkt_sent(self) -> Optional[int]:
        """
        Number of packets transmitted.
        :return:
        """
        return copy(self.__pkt_sent)

    @property
    def pkt_recv(self) -> Optional[int]:
        """
        Number of packets received.
        Returns:
            |int|:
        """
        return copy(self.__pkt_recv)

    @property
    def pkt_lost(self) -> Optional[int]:
        """
        Number of packet losses.
        :return: |int|: |None| if the value is not a number.
        """
        try:
            return cast(int, self.pkt_sent) - cast(int, self.pkt_recv)
        except TypeError:
            return None

    @property
    def pkt_loss_rate(self) -> Optional[float]:
        """
        Percentage of packet loss |percent_unit|.
        :return: |float|: |None| if the value is not a number.
        """
        try:
            return cast(int, self.pkt_lost) / cast(int, self.pkt_sent)
        except (TypeError, ZeroDivisionError, OverflowError):
            return None

    @property
    def rtt_min(self) -> Optional[float]:
        """
        Minimum round trip time of transmitted ICMP packets |msec_unit|.
        :return: float
        """
        return copy(self.__rtt_min)

    @property
    def rtt_avg(self) -> Optional[float]:
        """
        Average round trip time of transmitted ICMP packets |msec_unit|.
        :return:
        """

        return copy(self.__rtt_avg)

    @property
    def rtt_max(self) -> Optional[float]:
        """
        Maximum round trip time of transmitted ICMP packets |msec_unit|.
        :return:
        """
        return copy(self.__rtt_max)

    @property
    def rtt_mdev(self) -> Optional[float]:
        """
        Standard deviation of transmitted ICMP packets.
        :returns:
        """
        # QUESTION: Should it return None when parsing a Windows ping trace ?
        return self.__rtt_mdev

    @property
    def pkt_duplicates(self) -> Optional[int]:
        """
        Number of duplicated packets.
        :returns: an int
        """

        return self.__pkt_dupe

    @property
    def pkt_duplicate_rate(self) -> Optional[float]:
        """
        Percentage of duplicated packets |percent_unit|.
        :returns:
        """

        try:
            return cast(int, self.pkt_duplicates) / cast(int, self.pkt_recv)
        except (TypeError, ZeroDivisionError, OverflowError):
            return None

    # ===== ( Methods ) ================================================================================================

    def parse(self, ping_trace):
        """
        Parse a ping trace and fill this object

        :param ping_trace: a str containing the ping trace
        :return:
        """
        # Find the destination:
        match = re.search(RGX_DST, ping_trace)
        if match:
            self.__destination = match.group('dst')

        # Find the number of pkt sent:
        match = re.search(RGX_SENT_PKT, ping_trace)
        if match:
            self.__pkt_sent = int(match.group('count'))

        # Find the number of pkt received:
        match = re.search(RGX_RECV_PKT, ping_trace)
        if match:
            self.__pkt_recv = int(match.group('count'))

        # Find the loss count / rate:
        self.__pkt_lost = self.__pkt_sent - self.__pkt_recv

        # Find the destination:
        match = re.search(RGX_RTT, ping_trace)
        if match:
            self.__rtt_min  = float(match.group('min'))
            self.__rtt_max  = float(match.group('max'))
            self.__rtt_avg  = float(match.group('avg'))
            self.__rtt_mdev = float(match.group('mdev'))

        # TODO: add counting for duplicates
    # End def parse

    def as_dict(self) -> dict:
        """
        Return the dict representation of PingStats
        :returns: a dict
        """

        d = {
            "destination"            : self.destination,
            "packet_sent"           : self.pkt_sent,
            "packet_received"       : self.pkt_recv,
            "packet_loss_count"     : self.pkt_lost,
            "packet_loss_rate"      : self.pkt_loss_rate,
            "rtt_min"               : self.rtt_min,
            "rtt_avg"               : self.rtt_avg,
            "rtt_max"               : self.rtt_max,
            "rtt_mdev"              : self.rtt_mdev,
            "packet_duplicate_count": self.pkt_duplicates,
            "packet_duplicate_rate" : self.pkt_duplicate_rate,
        }
        return d
    # End def as_dict
# End class PingStats
