"""
This module contains the classes that are used to represent sockets and tokens. Sockets are an internal abstraction
that are used to represent qubits. Tokens are the external abstraction of qubits that is used at the NET layer.
A token is created when Link Layer protocols signal the generation of a new entangled pair.
"""

from collections import namedtuple

import netsquid as ns

__all__ = ['Socket', 'Token', 'TokenTable', 'TokenMessage']


# Socket = namedtuple('Socket', ['node', 'interface', 'idx'])

class Socket:
    r"""
    A socket is an internal logical abstraction for an entangled qubit. The name derives from the fact that
    the qubit is entangled with (at least) another qubit, and thus it represents one end of the entangling connection.

    Parameters
    ----------
    node : int
        The node the qubit is located on.
    qnic : int
        The interface the qubit is assigned on.
    idx : int
        The index of the qubit on the interface.
    """
    __name__ = 'Socket'

    _inner_tuple = namedtuple('Socket', ['node', 'qnic', 'idx', 'created_at'])

    def __init__(self, node, qnic, idx):
        self._data = self._inner_tuple(node, qnic, idx, ns.sim_time())

    @property
    def node(self):
        return self._data.node

    @property
    def qnic(self):
        return self._data.qnic

    @property
    def idx(self):
        return self._data.idx

    @property
    def created_at(self):
        return self._data.created_at

    def __eq__(self, other):
        return self.node == other.node and self.qnic == other.qnic and self.idx == other.idx and \
               self.created_at == other.created_at

    def __repr__(self):
        return f"Socket(node={self.node}, interface={self.qnic}, idx={self.idx}, created_at={self.created_at})"

    def __hash__(self):
        return hash(self.__repr__())


Token = namedtuple('Token', ['socket', 'other_end', 'current_state', 'pct', 'purified',
                             'additional_info'])
r"""
A token is an external logical abstraction for an entangled qubit. It is used at the NET layer to manage quantum
resources in a hardware-independent fashion.

Parameters
----------
socket : :class:`~progress.sockets.Socket`
    The local socket related to this token.
other_end : :class:`~progress.sockets.Socket`
    The other end of the entangled connection.
current_state : int
    The current state of the qubit (0 -> :math:`\vert\beta_{00}\rangle`, 1 -> :math:`\vert\beta_{01}\rangle`,
    2 -> :math:`\vert\beta_{10}\rangle`, 3 -> :math:`\vert\beta_{11}\rangle`).
pct : float
    The Pair Coherence Timeout of the socket pair.
purified : int
    Whether or not the socket is purified. 0 -> not purified, 1 -> purified, >1 -> number of purification rounds.
additional_info : dict[any, any]
    Additional information about the socket.
"""


class TokenMessage(ns.components.Message):
    r"""
    A message containing a token. Used to transfer tokens from a module to another.

    Parameters
    ----------
    token : :class:`~progress.sockets.Token`
        The token to be transmitted along with the message.
    """
    HEADER = "TOKEN MESSAGE"

    def __init__(self, token):
        super().__init__(items=[token], header=self.HEADER)

    @property
    def token(self):
        return self.items[0]

    def __repr__(self):
        return f"TokenMessage(token={self.token})"


def have_same_ends(token1, token2):
    r"""
    Check if two tokens represent sockets that are entangled among the same two devices.

    Parameters
    ----------
    token1 : :class:`~progress.sockets.Token`
        The first token.
    token2 : :class:`~progress.sockets.Token`
        The second token.

    Returns
    -------
    bool
    """
    return token1.socket.node == token2.socket.node and token1.other_end.node == token2.other_end.node


class TokenTable:
    """
    A table that stores tokens.
    This is used to keep track of the tokens that are currently owned by a specific module.
    """

    def __init__(self):
        self._table = []

    def get_snapshot(self):
        """
        Get a snapshot of the socket table.

        Returns
        -------
        list[:class:`~progress.sockets.Token`]
            The list of tokens in the table.
        """
        return self._table.copy()

    def add_token(self, token):
        r"""
        Add a socket descriptor to the socket table.

        Parameters
        ----------
        token : :class:`~progress.sockets.Token`
            The token to add.
        """
        self._table.append(token)

    def pop_token(self, local_end, raise_error=True):
        r"""
        Pop a token from the table identified by the local_end.
        If the token is not found, a ValueError is raised.

        Parameters
        ----------
        local_end : :class:`~progress.sockets.Socket`
            The local end of the token to pop.
        raise_error : bool
            Whether to raise a ValueError if the token is not found. If False, the function will return None.

        Returns
        -------
        :class:`~progress.sockets.Token`
            The socket descriptor that was popped.
        """
        for descriptor in self._table:
            if descriptor.socket == local_end:
                self._table.remove(descriptor)
                return descriptor
        if raise_error:
            raise ValueError(f"Token local end {local_end} not found.")
        else:
            return None

    def get_token(self, local_end, raise_error=True):
        r"""
        Get a token from the table identified by the local_end. Does not remove it from the table.

        Parameters
        ----------
        local_end : :class:`~progress.sockets.Socket`
            The local end of the token to get.
        raise_error : bool
            Whether to raise a ValueError if the token is not found. If False, the function will return None.

        Returns
        -------
        :class:`~progress.sockets.Token` or None
            The token that was found. None if the token was not found and raise_error is False.
        """
        for token in self._table:
            if token.socket == local_end:
                return token
        if raise_error:
            raise ValueError(f"Token local end {local_end} not found.")
        else:
            return None

    def replace_token(self, local_end, new_token, raise_error=True):
        r"""
        Replace a token in the table identified by its local end.

        Parameters
        ----------
        local_end : :class:`~progress.sockets.Socket`
            The local end of the socket descriptor to replace.
        new_token : :class:`~progress.sockets.Token`
            The new descriptor to replace the old one with.
        raise_error : bool
            Whether to raise a ValueError if the socket is not found. If False, the function will return False.

        Returns
        -------
        bool
            Whether or not the socket was found and replaced.
        """
        for token in self._table:
            if token.local_end == local_end:

                third_desc = Token(token.local_end, new_token.other_end,
                                   new_token.current_state, min(token.pct, new_token.pct),
                                   new_token.purified, new_token.additional_info)

                self._table.remove(token)
                self._table.append(third_desc)
                return True

            if raise_error:
                raise ValueError(f"Token with local end {local_end} not found.")
            else:
                return False

    def collect_garbage(self, current_time):
        r"""
        Remove all expired tokens from the token table.

        Parameters
        ----------
        current_time : float
            The current time in the simulation. [ns]

        Returns
        -------
        list[:class:`~progress.sockets.Token`]
            The list of tokens that were removed.
        """
        to_remove = []
        for token in self._table:
            if token.pct <= current_time:
                to_remove.append(token)
        for token in to_remove:
            self._table.remove(token)
        return to_remove

    def get_target_token(self, other_end_node, additional_info_filters=None, policy="LRTF"):
        r"""
        Get a token having a specific other end node.

        Parameters
        ----------
        other_end_node : int or list[int]
            The other end node of the token to get. if a list is provided, the first token
            with a matching other end node is returned.
        additional_info_filters : dict
            A dictionary of filters to apply to the additional info of the token.
        policy : str
            The policy to use when selecting the socket.
            Currently only "LRTF" (Longest Remaining Time First) is supported.

        Returns
        -------
        :class:`~progress.sockets.Token` or None
            The socket descriptor with the specified other end node. `None` if not found
        """
        if policy == "LRTF":
            return self._get_target_descriptor_LRTF(other_end_node, additional_info_filters)
        else:
            raise ValueError("Policy not supported.")

    def _get_target_descriptor_LRTF(self, other_end_node, additional_info_filters=None):
        r"""
        Get the token having a specific other end node. In case of multiple choices, the one with the
        highest pct is returned.

        Parameters
        ----------
        other_end_node : int or list[int]
            The other end node of the token to get. if a list is provided, the first token
            with a matching other end node is returned.
        additional_info_filters : dict
            A dictionary of filters to apply to the additional info of the token.

        Returns
        -------
        :class:`progress.sockets.Token` or None
            The token with the specified other end node. `None` if not found
        """
        if isinstance(other_end_node, int):
            other_end_node = [other_end_node]
        # Find the socket descriptor with the longest remaining time
        max_pct = 0
        picked_token = None
        for token in self._table:
            if token.other_end.node in other_end_node and token.pct >= max_pct:
                if additional_info_filters is not None:
                    discard = False
                    for key, value in additional_info_filters.items():
                        if key not in token.additional_info or token.additional_info[key] != value:
                            discard = True
                            break
                    if discard:
                        continue
                max_pct = token.pct
                picked_token = token
        return picked_token
