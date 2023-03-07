import netsquid as ns

import sdqn.progress.repository


class TokenUtilizationMetricsCollector:
    """
    This class is responsible for collecting service time metrics about user requests in the simulation.
    It collects metrics about requests between two specified nodes.
    """

    def __init__(self):
        self.data_collector = ns.util.DataCollector(get_data_function=self.handle_trigger)

        ev_expr_new_token = ns.pydynaa.core.EventExpression(
            event_type=sdqn.progress.repository.WaitForSwappingModuleBehavior.NEW_TOKEN_EVT_TYPE)

        freed_token = ns.pydynaa.core.EventExpression(
            event_type=sdqn.progress.repository.FreeEverythingModuleBehavior.FREED_TOKEN_EVT_TYPE)

        self.data_collector.collect_on(triggers=[ev_expr_new_token, freed_token], combine_rule="OR")

    @staticmethod
    def handle_new_token(ev_expr):
        protocol = ev_expr.triggered_events[-1].source
        result = protocol.get_signal_result(sdqn.progress.repository.WaitForSwappingModuleBehavior.NEW_TOKEN_SIGNAL)
        return {'time': result[0], 'type': 'new_token'}

    @staticmethod
    def handle_freed_token(ev_expr):
        protocol = ev_expr.triggered_events[-1].source
        result = protocol.get_signal_result(sdqn.progress.repository.FreeEverythingModuleBehavior.FREED_TOKEN_SIGNAL)
        return {'time': result[0], 'type': 'freed_token'}

    def handle_trigger(self, ev_expr):
        protocol = ev_expr.triggered_events[-1].source

        if isinstance(protocol, sdqn.progress.repository.WaitForSwappingModuleBehavior):
            return self.handle_new_token(ev_expr)
        elif isinstance(protocol, sdqn.progress.repository.FreeEverythingModuleBehavior):
            return self.handle_freed_token(ev_expr)

    def get_counts(self):
        dataframe = self.data_collector.dataframe

        grouped = dataframe.groupby('type', as_index=True).count()
        print(grouped)
        return grouped['time'][0], grouped['time'][1]
