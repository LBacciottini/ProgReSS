"""
Some popular, ready-to-use, module behaviors for the DAG
"""
import netsquid as ns
from sdqn.progress.p_module import ProcessingModuleBehavior, SchedulingModuleBehavior
from sdqn.sockets import Token
import sdqn.sdqn_logging as log


class EntanglementSwappingModuleBehavior(ProcessingModuleBehavior):
    r"""
    This class implements the behavior of a module that performs the entanglement swapping protocol.
    """

    def __init__(self, dest_devices, dest_module_ids, name, node, qnic=None):
        r"""
        Initialize the behavior of the module.

        Parameters
        ----------
        dest_devices : tuple
            A tuple with the two lists of IDs identifying the device pools among which swapping must be carried out.
            The module swaps tokens entangled with one device from the first pool with tokens
            entangled with one device from the second pool.
        dest_module_ids : tuple
            A tuple with the two lists of IDs of the modules on the destination devices that the swapping outcome must
            be sent to. Each element of each list refers to the matching element of the device pool.
            They are supposed to be instances of :class:`~sdqn.progress.repository.WaitForSwappingModuleBehavior`.
        name : str
            The name of the module
        node : :class:`~sdqn.progress.p_module.Module`
            The module that this behavior is attached to
        qnic : int or None, optional
            See :class:`~sdqn.progress.p_module.ModuleBehavior`.
        """
        self.dest_devices = dest_devices
        self.dest_module_ids = dest_module_ids
        self._swapped_ends = dest_devices
        super().__init__(name=name, node=node, qnic=qnic)

    def handle_new_token(self, request):
        token = request.token
        target_pool_index = 0 if token.other_end.node in self.dest_devices[1] else 1
        target_pool = self.dest_devices[target_pool_index]

        # look in the token table for a token that is waiting to be swapped
        target_token = self.node.token_table.get_target_token(target_pool)
        if target_token is None:
            # if no token is found, store the token in the token table
            self.node.token_table.add_token(token)
            return
        # pop the target token from the token table
        self.node.token_table.pop_token(local_end=target_token.socket)

        # request entanglement swapping
        if target_pool_index == 1:
            self.swap_tokens(token, target_token)
        else:
            self.swap_tokens(target_token, token)

    @staticmethod
    def _get_state_after_swap(old_state_a, old_state_b, outcome):
        x_corr = 0
        z_corr = 0
        if old_state_a >= 2:
            z_corr += 1
        if old_state_b >= 2:
            z_corr += 1
        if outcome >= 2:
            z_corr += 1

        if old_state_a % 2 != 0:
            x_corr += 1
        if old_state_b % 2 != 0:
            x_corr += 1
        if outcome % 2 != 0:
            x_corr += 1

        x_corr %= 2
        z_corr %= 2
        return z_corr * 2 + x_corr

    def handle_response(self, request):
        # the response is the outcome of the entanglement swapping protocol
        # we assert that the response is a swapping outcome
        # assert request.request.__name__ == "req_swap"
        # tokens have already been freed by the swapping protocol. no need to check them out again
        # send the outcome to the destination module
        outcome = request.response
        # the INSTR_BELL_MEASURE outcome does not exactly match bell states indices.
        if outcome == 3:
            outcome = 2
        elif outcome == 2:
            outcome = 3

        # print("Device: {}, swapping outcome: {}".format(self.node.device_id, outcome))  # DEBUG

        # get the new state of the token
        new_state = self._get_state_after_swap(request.request.token1.current_state,
                                               request.request.token2.current_state,
                                               outcome)
        new_pct = min(request.request.token1.pct, request.request.token2.pct)

        message = ns.components.Message(items=[request.request.token1.other_end,
                                               request.request.token2.other_end,
                                               new_state, new_pct], header="swapping_outcome")

        dest_device_a = request.request.token1.other_end.node
        dest_module_id_a = self.dest_module_ids[0][self.dest_devices[0].index(dest_device_a)]
        dest_device_b = request.request.token2.other_end.node
        dest_module_id_b = self.dest_module_ids[1][self.dest_devices[1].index(dest_device_b)]

        # DEBUG
        """
        print("Device: {}, dests are ({},{}), ({},{})"
              .format(self.node.device_id, dest_device_a, dest_module_id_a, dest_device_b, dest_module_id_b))
        """

        self.send_message(message=message, dest_device=dest_device_a, dest_module_id=dest_module_id_a)
        self.send_message(message=message, dest_device=dest_device_b, dest_module_id=dest_module_id_b)

    def handle_message(self, request):
        raise NotImplementedError("This module does not receive messages")


class WaitForSwappingModuleBehavior(SchedulingModuleBehavior):
    """
    This class implements the behavior of a module that waits for the outcome of the entanglement swapping protocol.
    """

    NEW_TOKEN_SIGNAL = "new_token"
    NEW_TOKEN_EVT_TYPE = ns.pydynaa.EventType("new_token", "A token has been captured by this module")
    """
    Label used to signal that a token has been captured.
    """

    def __init__(self, name, node, output_map=None, qnic=None, collect_stats=False):
        r"""
        Initialize the behavior of the module.

        Parameters
        ----------
        name : str
            The name of the module
        node : :class:`~sdqn.progress.p_module.Module`
            The module that this behavior is attached to
        output_map : dict or None, optional
            A dictionary that maps each possible new remote entangled node to a different output port
            of the module. If None, all tokens are sent to the first output port.
        qnic : int or None, optional
            See :class:`~sdqn.progress.p_module.ModuleBehavior`.
        collect_stats : bool, optional
            Whether to collect statistics about the module's behavior.
        """
        super().__init__(name=name, node=node, qnic=qnic)
        self.output_map = output_map
        self.collect_stats = collect_stats
        if collect_stats:
            self.add_signal(self.NEW_TOKEN_SIGNAL, self.NEW_TOKEN_EVT_TYPE)

    def handle_message(self, request):
        # the message is the outcome of the entanglement swapping protocol
        # we assert that the message is a swapping outcome

        assert request.message.meta["header"] == "swapping_outcome"

        # get the two ends that were swapped
        end_a = request.message.items[0]
        end_b = request.message.items[1]
        new_pct = request.message.items[3]
        new_state = request.message.items[2]
        # check which end is the local end
        local_end = end_a if end_a.node == self.node.device_id else end_b
        # check which end is the remote end
        remote_end = end_a if end_a.node != self.node.device_id else end_b
        # get the token for the local end
        token = self.node.token_table.get_token(local_end)
        # update the token information
        new_token = Token(socket=local_end, other_end=remote_end, pct=new_pct, purified=0, current_state=new_state,
                          additional_info=token.additional_info)
        # promote the token
        if self.output_map is None:
            self.promote_token(new_token)
        else:
            self.promote_token(new_token, output_port=self.output_map[remote_end.node])

    def handle_new_token(self, request):
        # simply store the token in the token table
        if self.collect_stats:
            sig_result = (ns.sim_time(), request.token.other_end.node, request.token.socket.created_at, request.token)
            self.send_signal(self.NEW_TOKEN_SIGNAL, sig_result)

        self.node.token_table.add_token(request.token)

    def handle_response(self, request):
        raise NotImplementedError("This module does not receive responses")


class DEJMPSModuleBehavior(ProcessingModuleBehavior):
    r"""
    This class implements the behavior of a module that performs the DEJMPS protocol.
    """

    def __init__(self, module_id, dest_device, dest_module_id, is_solicitor, name, node, qnic=None):
        r"""
        Initialize the behavior of the module.

        Parameters
        ----------
        module_id : int
            The ID of the module
        dest_device : int
            The ID of the device that the distillation outcome must be sent to
        dest_module_id : int
            The ID of the module on the destination device that the distillation outcome must be sent to
        is_solicitor : bool
            Whether the module is the solicitor or not
        name : str
            The name of the module
        node : :class:`~sdqn.progress.p_module.Module`
            The module that this behavior is attached to
        qnic : int or None, optional
            See :class:`~sdqn.progress.p_module.ModuleBehavior`.
        """
        self.module_id = module_id
        self.dest_device = dest_device
        self.dest_module_id = dest_module_id
        self.is_solicitor = is_solicitor
        self._stored_outcomes = {}
        super().__init__(name=name, node=node, qnic=qnic)

    def handle_new_token(self, request):
        token = request.token
        if not self.is_solicitor:
            # if the module is not the solicitor, it must wait for a message from the solicitor
            # the message will contain the token to be distilled
            self.node.token_table.add_token(token)
            return
        # if the module is the solicitor, it must check whether a new distillation can be carried out
        # look in the token table for a token that is waiting to be distilled

        target_token = self.node.token_table.get_target_token(token.other_end.node,
                                                              additional_info_filters={"dejmps_pending": False})
        token.additional_info["dejmps_pending"] = False
        self.node.token_table.add_token(token)

        if target_token is not None:
            # pop the target token from the token table (it will be used as ancilla anyway)
            self.node.token_table.pop_token(local_end=target_token.socket)
            token.additional_info["dejmps_pending"] = True
            target_token.additional_info["dejmps_pending"] = True
            # request distillation
            self.dejmps_tokens(token, target_token, role='A')

    def handle_response(self, request):
        # the response is the outcome of the DEJMPS protocol
        # we assert that the response is a DEJMPS outcome
        # assert request.request.__name__ == "req_dejmps"
        # tokens have already been freed by the DEJMPS protocol. no need to check them out again

        outcome = request.response
        other_end_a = request.request.token1.other_end
        other_end_b = request.request.token2.other_end
        local_end_a = request.request.token1.socket

        if self.is_solicitor:
            # if the module is the solicitor, it must send the outcome to the destination module
            message = ns.components.Message(items=[other_end_a, other_end_b, outcome], header="dejmps_solicitation")
            self.send_message(message=message, dest_device=self.dest_device, dest_module_id=self.dest_module_id)

            # store the outcome
            self._stored_outcomes[(other_end_a, other_end_b)] = outcome

        else:
            # retrieve the stored outcome from the other end
            stored_outcome = self._stored_outcomes[(other_end_a, other_end_b)]
            del self._stored_outcomes[(other_end_a, other_end_b)]

            success = (outcome == stored_outcome)

            message = ns.components.Message(items=[other_end_a, success], header="dejmps_outcome")
            self.send_message(message=message, dest_device=self.dest_device, dest_module_id=self.dest_module_id)
            # log.info(f"Sending DEJMPS outcome {message} for {other_end_a} to {self.dest_device} {self.dest_module_id}", repeater_id=self.node.device_id)

            if success:
                # in case of success we promote the distilled token
                token = self.node.token_table.get_token(local_end=local_end_a)
                self.promote_token(token)

    def handle_message(self, request):

        if self.is_solicitor:
            # the solicitor can only receive "dejmps_outcome" messages
            if request.message.meta["header"] == "dejmps_outcome":
                success = request.message.items[1]
                if success:
                    # in case of success we promote the distilled token
                    token = self.node.token_table.get_token(local_end=request.message.items[0])
                    # log.info(f"Received distillation outcome for token {token}", repeater_id=self.node.device_id)
                    del token.additional_info["dejmps_pending"]
                    self.promote_token(token)
                else:
                    # in case of failure we must free the tokens
                    token = self.node.token_table.pop_token(local_end=request.message.items[0])
                    self.free_token(token)

        else:
            # the non-solicitor can only receive "dejmps_solicitation" messages
            if request.message.meta["header"] == "dejmps_solicitation":
                # retrieve the token to be distilled
                token_a = self.node.token_table.get_token(local_end=request.message.items[0])
                token_b = self.node.token_table.get_token(local_end=request.message.items[1])

                # log.info(f"Received distillation solicit for tokens {token_a} and {token_b}", repeater_id=self.node.device_id)

                # pop token_b from the token table
                self.node.token_table.pop_token(local_end=token_b.socket)

                # store the outcome in the solicitation message
                outcome = request.message.items[2]
                self._stored_outcomes[(token_a.other_end, token_b.other_end)] = outcome

                # request distillation
                self.dejmps_tokens(token_a, token_b, role='B')


class RoundRobinSchedulingModuleBehavior(SchedulingModuleBehavior):
    r"""
    This class implements the behavior of a module that performs a simple, non-blocking, round-robin
    scheduling of tokens among output ports.
    """

    def __init__(self, name, node, qnic=None):
        r"""
        Initialize the behavior of the module.

        Parameters
        ----------
        name : str
            The name of the module
        node : :class:`~sdqn.progress.p_module.Module`
            The module that this behavior is attached to
        qnic : int or None, optional
            See :class:`~sdqn.progress.p_module.ModuleBehavior`.
        """
        super().__init__(name=name, node=node, qnic=qnic)
        self._next_out_index = 0

    def _get_next_out_idx(self, token=None):
        if token is None:
            ret = self._next_out_index
            self._next_out_index = (self._next_out_index + 1) % self.node.num_output
            return ret
        else:
            # return a simple hash of the token
            return hash(token) % self.node.num_output

    def handle_new_token(self, request):
        out_index = self._get_next_out_idx()
        # log.info(f"Promoting token {request.token} to output port {out_index}", repeater_id=self.node.device_id)
        self.promote_token(request.token, output_port=out_index)

    def handle_response(self, request):
        raise NotImplementedError("This module does not receive responses")

    def handle_message(self, request):
        raise NotImplementedError("This module does not receive messages")


class FreeEverythingModuleBehavior(ProcessingModuleBehavior):
    r"""
    This class implements the behavior of a dummy module that frees all tokens.
    """

    FREED_TOKEN_SIGNAL = "freed_token"
    FREED_TOKEN_EVT_TYPE = ns.pydynaa.EventType("freed_token", "A token has been freed by this module")
    """
    Label used to signal that a token has been freed.
    """

    def __init__(self, name, node, qnic=None, collect_stats=False):
        r"""
        Initialize the behavior of the module.

        Parameters
        ----------
        name : str
            The name of the module
        node : :class:`~sdqn.progress.p_module.Module`
            The module that this behavior is attached to
        qnic : int or None, optional
            See :class:`~sdqn.progress.p_module.ModuleBehavior`.
        collect_stats : bool, optional
            Whether to collect statistics about the freed tokens.
        """
        super().__init__(name=name, node=node, qnic=qnic)
        self.collect_stats = collect_stats
        if self.collect_stats:
            self.add_signal(self.FREED_TOKEN_SIGNAL, self.FREED_TOKEN_EVT_TYPE)

    def handle_new_token(self, request):
        # log.info("Freeing token {}".format(request.token), repeater_id=self.node.device_id)
        if self.collect_stats:
            sig_result = (ns.sim_time(), request.token.other_end.node, request.token.socket.created_at, request.token)
            self.send_signal(self.FREED_TOKEN_SIGNAL, sig_result)
        self.free_token(request.token)

    def handle_response(self, request):
        raise NotImplementedError("This module does not receive responses")

    def handle_message(self, request):
        raise NotImplementedError("This module does not receive messages")


class ShortCircuitModuleBehavior(SchedulingModuleBehavior):
    r"""
    This class implements the behavior of a dummy module that promotes all tokens to its first output port.
    """

    def __init__(self, name, node, qnic=None):
        r"""
        Initialize the behavior of the module.

        Parameters
        ----------
        name : str
            The name of the module
        node : :class:`~sdqn.progress.p_module.Module`
            The module that this behavior is attached to
        qnic : int or None, optional
            See :class:`~sdqn.progress.p_module.ModuleBehavior`.
        """
        super().__init__(name=name, node=node, qnic=qnic)

    def handle_new_token(self, request):
        out_index = 0
        self.promote_token(request.token, output_port=out_index)

    def handle_response(self, request):
        raise NotImplementedError("This module does not receive responses")

    def handle_message(self, request):
        raise NotImplementedError("This module does not receive messages")