"""
A dummy controller that has some pre-loaded DAGS and can send them to the devices
"""
import random

from sdqn.messaging.messages import ClassicalRoutingTableMessage
from sdqn.progress.messages import ReplaceDAGMessage
from sdqn.progress.repository import *
from sdqn.progress.dag import DAGFactory
from sdqn import sdqn_logging as log

import netsquid as ns

__all__ = ["DummyController"]


def get_dag_factory(node, scenario):
    if node == 0:
        if scenario == 0 or scenario == 1:
            module_0 = DEJMPSModuleBehavior
            params_0 = {"qnic": 0, "name": "dejmps_0", "module_id": 0, "dest_device": 2, "dest_module_id": 0,
                        "is_solicitor": False}
            module_1 = WaitForSwappingModuleBehavior
            params_1 = {"name": "wait_for_swapping_1"}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}

            module_3 = FreeEverythingModuleBehavior
            params_3 = {"name": "free_everything_3"}

            edges = [("0", "1"), ("1", "2"), ("2", "3")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3)}
            return DAGFactory(edges, behaviors, device_id=0)

        elif scenario == 2 or scenario == 3:
            module_0 = ShortCircuitModuleBehavior
            params_0 = {"name": "short_circuit_0", "qnic": 0}
            module_1 = WaitForSwappingModuleBehavior
            params_1 = {"name": "wait_for_swapping_1"}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}

            module_3 = FreeEverythingModuleBehavior
            params_3 = {"name": "free_everything_3"}

            edges = [('0', '1'), ('1', '2'), ('2', '3')]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3)}
            return DAGFactory(edges, behaviors, device_id=0)

    elif node == 1:
        if scenario == 0 or scenario == 2:
            module_0 = DEJMPSModuleBehavior
            params_0 = {"qnic": 0, "name": "dejmps_0", "module_id": 0, "dest_device": 2, "dest_module_id": 1,
                        "is_solicitor": False}
            module_1 = WaitForSwappingModuleBehavior
            params_1 = {"name": "wait_for_swapping_1"}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}

            module_3 = FreeEverythingModuleBehavior
            params_3 = {"name": "free_everything_3"}

            edges = [("0", "1"), ("1", "2"), ("2", "3")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3)}
            return DAGFactory(edges, behaviors, device_id=1)

        elif scenario == 1 or scenario == 3:
            module_0 = ShortCircuitModuleBehavior
            params_0 = {"name": "short_circuit_0", "qnic": 0}
            module_1 = WaitForSwappingModuleBehavior
            params_1 = {"name": "wait_for_swapping_1"}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}

            module_3 = FreeEverythingModuleBehavior
            params_3 = {"name": "free_everything_3"}

            edges = [('0', '1'), ('1', '2'), ('2', '3')]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3)}
            return DAGFactory(edges, behaviors, device_id=1)

    elif node == 2:
        if scenario == 0:
            module_0 = DEJMPSModuleBehavior
            params_0 = {"qnic": 0, "name": "dejmps_0", "module_id": 0, "dest_device": 0, "dest_module_id": 0,
                        "is_solicitor": True}
            module_1 = DEJMPSModuleBehavior
            params_1 = {"qnic": 1, "name": "dejmps_1", "module_id": 1, "dest_device": 1, "dest_module_id": 0,
                        "is_solicitor": True}
            module_2 = DEJMPSModuleBehavior
            params_2 = {"qnic": 2, "name": "dejmps_2", "module_id": 2, "dest_device": 3, "dest_module_id": 0,
                        "is_solicitor": False}
            module_3 = DEJMPSModuleBehavior
            params_3 = {"qnic": 3, "name": "dejmps_3", "module_id": 3, "dest_device": 4, "dest_module_id": 0,
                        "is_solicitor": False}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([0, 1], [3, 4]),
                        "dest_module_ids": ([1, 1], [2, 2])}
            edges = [("0", "4"), ("1", "4"), ("2", "4"), ("3", "4")]

            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=2)

        elif scenario == 3:
            module_0 = ShortCircuitModuleBehavior
            params_0 = {"qnic": 0, "name": "dummy_0"}
            module_1 = ShortCircuitModuleBehavior
            params_1 = {"qnic": 1, "name": "dummy_1"}
            module_2 = ShortCircuitModuleBehavior
            params_2 = {"qnic": 2, "name": "dummy_2"}
            module_3 = ShortCircuitModuleBehavior
            params_3 = {"qnic": 3, "name": "dummy_3"}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([0, 1], [3, 4]),
                        "dest_module_ids": ([1, 1], [2, 2])}
            edges = [("0", "4"), ("1", "4"), ("2", "4"), ("3", "4")]

            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=2)

        elif scenario == 1:
            module_0 = DEJMPSModuleBehavior
            params_0 = {"qnic": 0, "name": "dejmps_0", "module_id": 0, "dest_device": 0, "dest_module_id": 0,
                        "is_solicitor": True}
            module_1 = ShortCircuitModuleBehavior
            params_1 = {"qnic": 1, "name": "dummy_1"}
            module_2 = DEJMPSModuleBehavior
            params_2 = {"qnic": 2, "name": "dejmps_2", "module_id": 2, "dest_device": 3, "dest_module_id": 0,
                        "is_solicitor": False}
            module_3 = ShortCircuitModuleBehavior
            params_3 = {"qnic": 3, "name": "dummy_3"}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_5", "dest_devices": ([0], [3]),
                        "dest_module_ids": ([1], [2])}
            module_5 = EntanglementSwappingModuleBehavior
            params_5 = {"name": "entanglement_swapping_6", "dest_devices": ([1], [4]),
                        "dest_module_ids": ([1], [2])}
            edges = [("0", "4"), ("1", "5"), ("2", "4"), ("3", "5")]

            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4),
                         '5': (module_5, params_5)}
            return DAGFactory(edges, behaviors, device_id=2)

        elif scenario == 2:
            module_0 = ShortCircuitModuleBehavior
            params_0 = {"qnic": 0, "name": "dummy_0"}
            module_1 = DEJMPSModuleBehavior
            params_1 = {"qnic": 1, "name": "dejmps_1", "module_id": 1, "dest_device": 1, "dest_module_id": 0,
                        "is_solicitor": True}
            module_2 = ShortCircuitModuleBehavior
            params_2 = {"qnic": 2, "name": "dummy_2"}
            module_3 = DEJMPSModuleBehavior
            params_3 = {"qnic": 3, "name": "dejmps_3", "module_id": 3, "dest_device": 4, "dest_module_id": 0,
                        "is_solicitor": False}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_5", "dest_devices": ([0], [3]),
                        "dest_module_ids": ([1], [2])}
            module_5 = EntanglementSwappingModuleBehavior
            params_5 = {"name": "entanglement_swapping_6", "dest_devices": ([1], [4]),
                        "dest_module_ids": ([1], [2])}
            edges = [("0", "4"), ("1", "5"), ("2", "4"), ("3", "5")]

            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4),
                         '5': (module_5, params_5)}
            return DAGFactory(edges, behaviors, device_id=2)

    elif node == 3:
        if scenario == 0:
            module_0 = DEJMPSModuleBehavior
            params_0 = {"qnic": 0, "name": "dejmps_0", "module_id": 0, "dest_device": 2, "dest_module_id": 2,
                        "is_solicitor": True}
            module_1 = DEJMPSModuleBehavior
            params_1 = {"qnic": 1, "name": "dejmps_1", "module_id": 1, "dest_device": 5, "dest_module_id": 1,
                        "is_solicitor": False}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}
            module_3 = WaitForSwappingModuleBehavior
            params_3 = {"name": "wait_for_swapping_3"}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([0, 1], [6]),
                        "dest_module_ids": ([2, 2], [2])}
            edges = [("0", "2"), ("1", "3"), ("2", "4"), ("3", "4")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=3)

        elif scenario == 1:
            module_0 = DEJMPSModuleBehavior
            params_0 = {"qnic": 0, "name": "dejmps_0", "module_id": 0, "dest_device": 2, "dest_module_id": 2,
                        "is_solicitor": True}
            module_1 = DEJMPSModuleBehavior
            params_1 = {"qnic": 1, "name": "dejmps_1", "module_id": 1, "dest_device": 5, "dest_module_id": 1,
                        "is_solicitor": False}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}
            module_3 = WaitForSwappingModuleBehavior
            params_3 = {"name": "wait_for_swapping_3"}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([0, 1], [6]),
                        "dest_module_ids": ([2, 2], [3])}
            edges = [("0", "2"), ("1", "3"), ("2", "4"), ("3", "4")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=3)

        elif scenario == 3:
            module_0 = ShortCircuitModuleBehavior
            params_0 = {"qnic": 0, "name": "short_circuit_0"}
            module_1 = ShortCircuitModuleBehavior
            params_1 = {"qnic": 1, "name": "short_circuit_1"}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}
            module_3 = WaitForSwappingModuleBehavior
            params_3 = {"name": "wait_for_swapping_3"}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([0, 1], [6]),
                        "dest_module_ids": ([2, 2], [2])}
            edges = [("0", "2"), ("1", "3"), ("2", "4"), ("3", "4")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=3)

        elif scenario == 2:
            module_0 = ShortCircuitModuleBehavior
            params_0 = {"qnic": 0, "name": "short_circuit_0"}
            module_1 = ShortCircuitModuleBehavior
            params_1 = {"qnic": 1, "name": "short_circuit_1"}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}
            module_3 = WaitForSwappingModuleBehavior
            params_3 = {"name": "wait_for_swapping_3"}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([0, 1], [6]),
                        "dest_module_ids": ([2, 2], [3])}
            edges = [("0", "2"), ("1", "3"), ("2", "4"), ("3", "4")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=3)

    elif node == 4:
        if scenario == 0:
            module_0 = DEJMPSModuleBehavior
            params_0 = {"qnic": 0, "name": "dejmps_0", "module_id": 0, "dest_device": 2, "dest_module_id": 3,
                        "is_solicitor": True}
            module_1 = DEJMPSModuleBehavior
            params_1 = {"qnic": 1, "name": "dejmps_1", "module_id": 1, "dest_device": 5, "dest_module_id": 2,
                        "is_solicitor": False}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}
            module_3 = WaitForSwappingModuleBehavior
            params_3 = {"name": "wait_for_swapping_3"}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([0, 1], [6]),
                        "dest_module_ids": ([2, 2], [2])}
            edges = [("0", "2"), ("1", "3"), ("2", "4"), ("3", "4")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=4)

        elif scenario == 2:
            module_0 = DEJMPSModuleBehavior
            params_0 = {"qnic": 0, "name": "dejmps_0", "module_id": 0, "dest_device": 2, "dest_module_id": 3,
                        "is_solicitor": True}
            module_1 = DEJMPSModuleBehavior
            params_1 = {"qnic": 1, "name": "dejmps_1", "module_id": 1, "dest_device": 5, "dest_module_id": 2,
                        "is_solicitor": False}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}
            module_3 = WaitForSwappingModuleBehavior
            params_3 = {"name": "wait_for_swapping_3"}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([0, 1], [6]),
                        "dest_module_ids": ([2, 2], [3])}
            edges = [("0", "2"), ("1", "3"), ("2", "4"), ("3", "4")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=4)

        elif scenario == 1:
            module_0 = ShortCircuitModuleBehavior
            params_0 = {"qnic": 0, "name": "short_circuit_0"}
            module_1 = ShortCircuitModuleBehavior
            params_1 = {"qnic": 1, "name": "short_circuit_1"}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}
            module_3 = WaitForSwappingModuleBehavior
            params_3 = {"name": "wait_for_swapping_3"}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([0, 1], [6]),
                        "dest_module_ids": ([2, 2], [3])}
            edges = [("0", "2"), ("1", "3"), ("2", "4"), ("3", "4")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=4)

        elif scenario == 3:
            module_0 = ShortCircuitModuleBehavior
            params_0 = {"qnic": 0, "name": "short_circuit_0"}
            module_1 = ShortCircuitModuleBehavior
            params_1 = {"qnic": 1, "name": "short_circuit_1"}
            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}
            module_3 = WaitForSwappingModuleBehavior
            params_3 = {"name": "wait_for_swapping_3"}
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([0, 1], [6]),
                        "dest_module_ids": ([2, 2], [2])}
            edges = [("0", "2"), ("1", "3"), ("2", "4"), ("3", "4")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=4)

    elif node == 5:
        if scenario == 0:
            module_0 = DEJMPSModuleBehavior
            params_0 = {"qnic": 0, "name": "dejmps_0", "module_id": 0, "dest_device": 6, "dest_module_id": 0,
                        "is_solicitor": False}
            module_1 = DEJMPSModuleBehavior
            params_1 = {"qnic": 1, "name": "dejmps_1", "module_id": 1, "dest_device": 3, "dest_module_id": 1,
                        "is_solicitor": True}
            module_2 = DEJMPSModuleBehavior
            params_2 = {"qnic": 2, "name": "dejmps_2", "module_id": 2, "dest_device": 4, "dest_module_id": 1,
                        "is_solicitor": True}
            module_3 = EntanglementSwappingModuleBehavior
            params_3 = {"name": "entanglement_swapping_4", "dest_devices": ([3, 4], [6]),
                        "dest_module_ids": ([3, 3], [1])}
            edges = [("0", "3"), ("1", "3"), ("2", "3")]

            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3)}
            return DAGFactory(edges, behaviors, device_id=5)

        elif scenario == 3:
            module_0 = ShortCircuitModuleBehavior
            params_0 = {"qnic": 0, "name": "dummy_0"}
            module_1 = ShortCircuitModuleBehavior
            params_1 = {"qnic": 1, "name": "dummy_1"}
            module_2 = ShortCircuitModuleBehavior
            params_2 = {"qnic": 2, "name": "dummy_2"}
            module_3 = EntanglementSwappingModuleBehavior
            params_3 = {"name": "entanglement_swapping_3", "dest_devices": ([3, 4], [6]),
                        "dest_module_ids": ([3, 3], [1, 1])}
            edges = [("0", "3"), ("1", "3"), ("2", "3")]

            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3)}
            return DAGFactory(edges, behaviors, device_id=5)

        elif scenario == 1:
            module_0 = RoundRobinSchedulingModuleBehavior
            params_0 = {"name": "round_robin_scheduling_0", "qnic": 0}

            module_1 = DEJMPSModuleBehavior
            params_1 = {"qnic": 1, "name": "dejmps_1", "module_id": 1, "dest_device": 3, "dest_module_id": 1,
                        "is_solicitor": True}

            module_2 = ShortCircuitModuleBehavior
            params_2 = {"qnic": 2, "name": "dummy_1"}
            
            module_3 = DEJMPSModuleBehavior
            params_3 = {"name": "dejmps_3", "module_id": 3, "dest_device": 6, "dest_module_id": 1,
                        "is_solicitor": False}
            
            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([3], [6]),
                        "dest_module_ids": ([3], [2])}
            
            module_5 = EntanglementSwappingModuleBehavior
            params_5 = {"name": "entanglement_swapping_5", "dest_devices": ([4], [6]),
                        "dest_module_ids": ([3], [2])}
            edges = [("0", "3"), ("0", "5"), ("1", "4"), ("2", "5"), ("3", "4")]

            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4), '5': (module_5, params_5)}
            return DAGFactory(edges, behaviors, device_id=5)

        elif scenario == 2:
            module_0 = RoundRobinSchedulingModuleBehavior
            params_0 = {"name": "round_robin_scheduling_0", "qnic": 0}

            module_1 = ShortCircuitModuleBehavior
            params_1 = {"qnic": 1, "name": "dummy_1"}

            module_2 = DEJMPSModuleBehavior
            params_2 = {"qnic": 2, "name": "dejmps_2", "module_id": 2, "dest_device": 4, "dest_module_id": 1,
                        "is_solicitor": True}

            module_3 = DEJMPSModuleBehavior
            params_3 = {"name": "dejmps_3", "module_id": 3, "dest_device": 6, "dest_module_id": 1,
                        "is_solicitor": False}

            module_4 = EntanglementSwappingModuleBehavior
            params_4 = {"name": "entanglement_swapping_4", "dest_devices": ([3], [6]),
                        "dest_module_ids": ([3], [2])}

            module_5 = EntanglementSwappingModuleBehavior
            params_5 = {"name": "entanglement_swapping_5", "dest_devices": ([4], [6]),
                        "dest_module_ids": ([3], [2])}
            edges = [("0", "4"), ("0", "3"), ("1", "4"), ("2", "5"), ("3", "5")]

            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4), '5': (module_5, params_5)}
            return DAGFactory(edges, behaviors, device_id=5)

    elif node == 6:
        if scenario == 0:
            module_0 = DEJMPSModuleBehavior
            params_0 = {"name": "dejmps_0", "module_id": 0, "dest_device": 5, "dest_module_id": 0,
                        "is_solicitor": True, "qnic": 0}

            module_1 = WaitForSwappingModuleBehavior
            params_1 = {"name": "wait_for_swapping_1", "collect_stats": True}

            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}

            module_3 = FreeEverythingModuleBehavior
            params_3 = {"name": "free_everything_3", "collect_stats": True}

            edges = [("0", "1"), ("1", "2"), ("2", "3")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3)}
            return DAGFactory(edges, behaviors, device_id=6)

        elif scenario == 1:
            module_0 = RoundRobinSchedulingModuleBehavior
            params_0 = {"name": "round_robin_scheduling_0", "qnic": 0}

            module_1 = DEJMPSModuleBehavior
            params_1 = {"name": "dejmps_1", "module_id": 1, "dest_device": 5, "dest_module_id": 3,
                        "is_solicitor": True}

            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2", "collect_stats": True}

            module_3 = WaitForSwappingModuleBehavior
            params_3 = {"name": "wait_for_swapping_3"}

            module_4 = FreeEverythingModuleBehavior
            params_4 = {"name": "free_everything_4", "collect_stats": True}

            edges = [("0", "1"), ("1", "2"), ("0", "2"), ("2", "3"), ("3", "4")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=6)

        elif scenario == 2:
            module_0 = RoundRobinSchedulingModuleBehavior
            params_0 = {"name": "round_robin_scheduling_0", "qnic": 0}

            module_1 = DEJMPSModuleBehavior
            params_1 = {"name": "dejmps_1", "module_id": 1, "dest_device": 5, "dest_module_id": 3,
                        "is_solicitor": True}

            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2", "collect_stats": True}

            module_3 = WaitForSwappingModuleBehavior
            params_3 = {"name": "wait_for_swapping_3"}

            module_4 = FreeEverythingModuleBehavior
            params_4 = {"name": "free_everything_4", "collect_stats": True}

            edges = [("0", "2"), ("1", "2"), ("0", "1"), ("2", "3"), ("3", "4")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3), '4': (module_4, params_4)}
            return DAGFactory(edges, behaviors, device_id=6)

        elif scenario == 3:
            module_0 = ShortCircuitModuleBehavior
            params_0 = {"name": "short_circuit_0", "qnic": 0}

            module_1 = WaitForSwappingModuleBehavior
            params_1 = {"name": "wait_for_swapping_1", "collect_stats": True}

            module_2 = WaitForSwappingModuleBehavior
            params_2 = {"name": "wait_for_swapping_2"}

            module_3 = FreeEverythingModuleBehavior
            params_3 = {"name": "free_everything_3", "collect_stats": True}

            edges = [("0", "1"), ("1", "2"), ("2", "3")]
            behaviors = {'0': (module_0, params_0), '1': (module_1, params_1), '2': (module_2, params_2),
                         '3': (module_3, params_3)}
            return DAGFactory(edges, behaviors, device_id=6)

    raise ValueError("Invalid node or scenario")


class DummyControllerProtocol(ns.protocols.NodeProtocol):

    NEW_SCENARIO_SIGNAL = "new_scenario"
    NEW_SCENARIO_EVT_TYPE = ns.pydynaa.EventType("new_scenario", "A new scenario has started")

    def __init__(self, node, avg_scenario_period=0.5):
        super().__init__(node=node, name="DummyControllerProtocol")
        self.avg_scenario_period = avg_scenario_period
        self.scenario = 0
        self.previous_scenario = -1
        self.add_signal(self.NEW_SCENARIO_SIGNAL, self.NEW_SCENARIO_EVT_TYPE)

    def run(self):

        # at the beginning the controller sends the classical routing table to each node
        routing_table_end_nodes = {
            0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0
        }
        routing_table_2 = {
            0: 0, 1: 1, 3: 2, 4: 3, 5: 2, 6: 2
        }
        routing_table_3 = {
            0: 0, 1: 0, 2: 0, 4: 0, 5: 1, 6: 1
        }
        routing_table_4 = {
            0: 0, 1: 0, 2: 0, 3: 0, 5: 1, 6: 1
        }
        routing_table_5 = {
            0: 1, 1: 1, 2: 1, 3: 1, 4: 2, 6: 0
        }

        routing_tables = [routing_table_end_nodes, routing_table_end_nodes.copy(),
                          routing_table_2, routing_table_3, routing_table_4, routing_table_5,
                          routing_table_end_nodes.copy()]

        for node in range(7):
            self.node.ports[f"dev_{node}"].tx_output(ClassicalRoutingTableMessage(dest_device=node,
                                                                                  routing_table=routing_tables[node]))

        topology_id = 0
        while True:

            # extract a random scenario between 0 and 3
            rng = ns.get_random_state()
            self.scenario = rng.randint(0, 4)
            # self.scenario = 0
            log.info("Scenario: " + str(self.scenario) + f" started. it will last until {ns.sim_time() + self.avg_scenario_period * 1e9} ns")

            # extract a random period as an exponential distribution
            # period = random.expovariate(1 / self.avg_scenario_period)*1e9
            period = self.avg_scenario_period * 1e9

            # send a new DAG to each node
            if self.previous_scenario != self.scenario:

                # for statistics collection
                result = (ns.sim_time(), self.scenario, topology_id)
                self.send_signal(self.NEW_SCENARIO_SIGNAL, result)

                self.previous_scenario = self.scenario
                for node in range(7):
                    dag_factory = get_dag_factory(node, self.scenario)
                    msg = ReplaceDAGMessage(destination_device=node, dag_factory=dag_factory, topology_id=topology_id)
                    self.node.ports[f"dev_{node}"].tx_output(msg)

                # wait for the period to expire
                topology_id += 1
            yield self.await_timer(duration=period)


class DummyController(ns.nodes.Node):

    def __init__(self, avg_scenario_period=0.5):
        super().__init__(name="DummyController")
        self.protocol = DummyControllerProtocol(self, avg_scenario_period=avg_scenario_period)

    def start(self):
        self.protocol.start()
