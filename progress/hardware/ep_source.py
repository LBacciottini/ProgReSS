"""
This module implements a source of entangled bell pairs which generates pairs according to the stochastic generation
process of Midpoint Source Protocol.
"""
import math

from netsquid.components.qsource import QSource, SourceStatus
from netsquid.components.models.delaymodels import DelayModel
import netsquid.qubits.ketstates as ks
from netsquid.nodes import Node
from netsquid.util.simtools import get_random_state
from netsquid.qubits import StateSampler
import netsquid as ns

__all__ = ["MPSSourceNode"]

from progress.hardware.llps.mps import MPSSourceProtocol
from progress import sdqn_logging as log


class MPSSource(QSource):
    r"""This source implements the Midpoint source (MS) protocols stochastic generation of entanglement. This class
    should be used only inside :class:`~qi_simulation.mps.components.ep_source.MPSSourceNode`.

    Parameters
    ----------
    name : str
        The name of this component.
    source : :class:`~qi_simulation.mps.components.ep_source.MPSSourceNode`
        The mid-point source that this instance is serving.
    p_left : float
        The probability of successfully latching the emitted qubit on the left with the components on that side.
        It should keep into account the loss probability on the link and the probability of failure at the components,
        which is due to frequency conversion and partial BSA in the case of standard MS,
        or due to imperfect nDPD and absorption in the case of AFC-enhanced MS.
    p_right : float, optional
        The probability of successfully latching the emitted qubit on the right with the components on that side.
        If ``None``, it is set equal to ``p_left``. Defaults to ``None``.
    p_mid : float, optional
        The probability that the midpoint entangled pair source successfully emits a pair at a given clock cycle.
        Defaults to 1.
    num_positions : int, optional
        The number of modes of the repeaters' quantum memories attached to the link. Defaults to 1.
    t_clock : int or float, optional
        The clock period of the MS protocols. Defaults to 1. [ns]
    t_link : int or float
        The total transmission time of the link between the two repeaters.
    """

    class MPSDelayModel(DelayModel):
        r"""
        This stateful delay model determines the time between the generation of two consecutive entangled pairs
        in MPS protocol. It should only be used inside its parent class
        :class:`~qi_simulation.mps.components.ep_source.MPSSource`.
        """

        def __init__(self, source,  p_left, p_right, num_positions, p_mid, t_clock, t_link, rng=None, **kwargs):
            self._p_left = p_left
            self._p_right = p_right
            self._num_positions = num_positions
            self._p_mid = p_mid
            self._t_clock = t_clock
            self._length = (t_link/1e9)*200000
            self._K = math.ceil(3/(min(p_left, p_right)*p_mid))
            self._t_link = t_link
            self._t_round = self._t_link + num_positions * self._K * t_clock
            self._last_bin_and_trial = (-1, -1)
            self._source = source
            super().__init__(rng=rng, **kwargs)
            self._successful_pairs = self._get_successful_pairs()
            self._first_time = True

        def generate_delay(self, **kwargs):

            if len(self._successful_pairs) > 0:
                bin_idx, trial_idx = self._successful_pairs.pop(0)
                last_bin, last_trial = self._last_bin_and_trial
                self._last_bin_and_trial = (bin_idx, trial_idx)

                # this is ugly but efficient to inform the node about the position of the generated entanglement
                self._source.subcomponents["qsource"].output_meta["position"] = bin_idx
                # this keeps the t_link updated on receiving nodes
                self._source.subcomponents["qsource"].output_meta["time_sent"] = ns.sim_time()

                # update status of qubit
                self._source.pos_status_list[bin_idx] = "busy"

                return self._get_inter_time(
                    old_bin=last_bin, old_trial=last_trial, new_bin=bin_idx, new_trial=trial_idx
                )

            else:
                self._successful_pairs = self._get_successful_pairs()
                if len(self._successful_pairs) == 0:

                    # used to inform that there was no successful trial in this round
                    self._source.subcomponents["qsource"].output_meta["position"] = -1
                    last_bin, last_trial = self._last_bin_and_trial
                    self._last_bin_and_trial = (-1, -1)

                    # used to notify that no trial was successful in the last round
                    self._source.subcomponents["qsource"].output_meta["position"] = -1

                    if last_bin == -1 and last_trial == -1:
                        return self._get_round_time()

                    return self._get_time_left_in_round(last_bin, last_trial) + self._get_round_time()
                else:
                    bin_idx, trial_idx = self._successful_pairs.pop(0)
                    last_bin, last_trial = self._last_bin_and_trial
                    self._last_bin_and_trial = (bin_idx, trial_idx)

                    # this is ugly but efficient to inform the node about the position of the generated entanglement
                    self._source.subcomponents["qsource"].output_meta["position"] = bin_idx

                    # update status of qubit
                    self._source.pos_status_list[bin_idx] = "busy"

                    delay = self._get_time_left_in_round(last_bin, last_trial) + self._get_inter_time(
                        old_bin=-1, old_trial=-1, new_bin=bin_idx, new_trial=trial_idx
                    )

                    return delay

        def _get_time_left_in_round(self, bin_idx, trial_idx):
            if bin_idx == -1 and trial_idx == -1:
                return 0
            full_bins_left = self._num_positions - bin_idx - 1
            trials_in_bin_left = self._K - trial_idx - 1
            return (trials_in_bin_left + self._K*full_bins_left)*self._t_clock + self._t_link

        def _get_round_time(self):
            return self._K * self._num_positions * self._t_clock + self._t_link

        def _get_inter_time(self, old_bin, old_trial, new_bin, new_trial):
            trials_in_bin_left = self._K - old_trial - 1
            full_bins_left = new_bin - old_bin - 1

            # no successes in last round, we behave as if we are at the beginning of the round
            if old_bin == -1 and old_trial == -1:
                trials_in_bin_left = 0

            ret = (trials_in_bin_left + full_bins_left * self._K + new_trial + 1) * self._t_clock
            if self._first_time:
                # because there is t_link/2 latency given by the qchannel and another t_link/2 must be added "manually"
                ret += self._t_link/2
                self._first_time = False
            return ret

        def _get_successful_pairs(self):
            """
            counter = 0
            for pairs in self._source.pos_status_list:
                if pairs == "free":
                    counter += 1
            if self._source.ID == 13:
                qilog.debug("{} free pairs found. Status are {}".format(counter, self._source.pos_status_list))
            """

            successful_pairs = []
            rng = self.rng
            if rng is None:
                rng = get_random_state()
            for i in range(self._num_positions):
                if self._source.pos_status_list[i] == "free":
                    trials_left = rng.geometric(self._p_left)
                    trials_right = rng.geometric(self._p_right)
                    if trials_left == trials_right:
                        gen_failures = rng.negative_binomial(trials_right, self._p_mid)
                        gen_trials = gen_failures + trials_right
                        if gen_trials <= self._K:
                            successful_pairs.append((i, gen_trials-1))  # bin_index and trial_index
            return successful_pairs

        def reset(self):
            self._last_bin_and_trial = (-1, -1)
            self._source.subcomponents["qsource"].output_meta["position"] = None
            for i, _ in enumerate(self._source.pos_status_list):
                self._source.pos_status_list[i] = "free"
            self._successful_pairs = self._get_successful_pairs()

    def __init__(self, name, source, t_link, p_left, p_right=None, p_mid=1., num_positions=1, t_clock=1, **kwargs):
        if p_right is None:
            p_right = p_left

        state_sampler = StateSampler([ks.b00], [1.])
        model_params = {"source": source, "p_left": p_left, "p_right": p_right, "num_positions": num_positions,
                        "p_mid": p_mid, "t_clock": t_clock, "t_link": t_link}
        timing = self.MPSDelayModel(**model_params)
        super().__init__(name, state_sampler=state_sampler, timing_model=timing, num_ports=2,
                         status=SourceStatus.OFF, **kwargs)

    def reset(self):
        self.subcomponents["internal_clock"].models["timing_model"].reset()


class MPSSourceNode(Node):
    r"""This node simulates the whole Midpoint source (MPS) protocols stochastic generation of entanglement.
        It keeps into account all the loss probabilities and only generates a pair when MPS would succeed
        in generating one. It is a way to implement the MPS protocol in a lightweight fashion, while maintaining all of
        its stochastic properties.

        Parameters
        ----------
        name : str
            The name of this node.
        p_left : float
            The probability of successfully latching the emitted qubit on the left with the components on that side.
            It should keep into account the loss probability on the link and the probability of failure at the components,
            which is due to frequency conversion and partial BSA in the case of standard MS,
            or due to imperfect nDPD and absorption in the case of AFC-enhanced MS.
        p_right : float, optional
            The probability of successfully latching the emitted qubit on the right with the components on that side.
            If ``None``, it is set equal to ``p_left``. Defaults to ``None``.
        num_positions : int, optional
            The number of modes of the repeaters' quantum memories attached to the link. Defaults to 1.
        p_mid : float, optional
            The probability that the midpoint entangled pair source successfully emits a pair at a given clock cycle.
            Defaults to 1.
        t_clock : int or float, optional
            The clock period of the MS protocols. Defaults to 1. [ns]
        rng : :class:`~numpy.random.RandomState`, optional
            The rng used in the stochastic generation of entangled pairs.
        """

    def __init__(self, name, p_left, p_right, num_positions, p_mid, t_clock, rng=None):
        port_names = ["qout0", "qout1", "c0", "c1"]
        super().__init__(name=name, port_names=port_names)
        self.pos_status_list = ["free" for _ in range(num_positions)]
        self.mps_params = {"p_left": p_left, "p_right": p_right, "num_positions": num_positions,
                           "p_mid": p_mid, "t_clock": t_clock, "rng": rng}
        protocol = MPSSourceProtocol(node=self)
        protocol.start()

    def init_source(self, t_link):
        qsource = MPSSource(f"{self.name}_inner_src", self, **self.mps_params, t_link=t_link)
        qsource.output_meta["position"] = None  # must be initialized
        qsource.output_meta["time_sent"] = ns.sim_time()
        self.add_subcomponent(qsource, name="qsource")
        qsource.ports["qout0"].forward_output(self.ports["qout0"])
        qsource.ports["qout1"].forward_output(self.ports["qout1"])

    def start(self):
        """
        Set the status of the inner source to INTERNAL so that it starts producing entanglement.
        """
        self.subcomponents["qsource"].status = SourceStatus.INTERNAL

    def stop(self):
        """
        Set the status of the inner source to OFF so that it stops producing entanglement.
        """
        self.subcomponents["qsource"].status = SourceStatus.OFF

    @property
    def status(self):
        """
        The status of the internal entangling quantum source.

        Returns
        -------
        :class:`netsquid.components.qsource.SourceStatus`
            The status of the source
        """
        return self.subcomponents["qsource"].status

    def reset(self, and_restart=True):
        """
        Reset the status of the inner source. Should be called while the inner source is OFF.

        Parameters
        ----------
        and_restart : bool, optional
            If True, also restarts the inner source, i.e. it sets its status to INTERNAL. Defaults to True.
        """
        qsource = self.subcomponents["qsource"]

        qsource.reset()

        if and_restart:
            qsource.status = SourceStatus.INTERNAL
