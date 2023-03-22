import logging

import netsquid as ns

from sdqn.examples.fish_network.topology import get_topology
import sdqn.sdqn_logging as log
from bulk_executor import TDRCollector

# the main function
if __name__ == '__main__':
    in_band_controller_dists = [15, 40]
    out_of_band_controller_dists = [5, 15]
    avg_periods = [0.0004, 0.0008, 0.0016, 0.0032, 0.0064, 0.0128]
    seeds = [53, 54, 55, 56, 57, 58, 59, 60, 61, 62]
    results = {15: [], 40: [], 100: []}
    repetitions = 35
    """
    for cd in controller_dists:
        ns.set_qstate_formalism(ns.QFormalism.DM)
        log.log_to_console(level=logging.INFO)
        tdr_s = []
        for idx, avg_period in enumerate(avg_periods):
            ns.sim_reset()
            ns.set_random_state(seed=seeds[idx])
            network, data_collector, fid_collector, agg_collector = get_topology(avg_scenario_period=avg_period,
                                                                                 controller_dist=cd,
                                                                                 out_of_band=False)
            stats = ns.sim_run(end_time=128000000)
            partial, total = data_collector.get_counts()
            tdr_s.append(partial / total)
            results[cd] = tdr_s
            print(f"Controller distance: {cd}, avg period: {avg_period}, TDR: {tdr_s[-1]}")
            fid_collector.plot_fidelity()
            agg_collector.plot_boxes()

        print(f"Controller distance: {cd}, TDR: {tdr_s}")
    print(results)
    """
    executor = TDRCollector(in_band_ctrl_dists=in_band_controller_dists,
                            out_of_band_ctrl_dists=out_of_band_controller_dists,
                            state_periods=avg_periods,
                            repetitions=repetitions)
    executor.run()
    executor.collect()