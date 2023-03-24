import netsquid as ns
import pandas as pd
import matplotlib.pyplot as plt

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
        if len(grouped['time']) < 2:
            print("WARNING: not enough data to compute token utilization")
            return 0, 1
        return grouped['time'][0], grouped['time'][1]


class FidelityMetricsCollector:
    """
    This class is responsible for collecting fidelity metrics about end-to-end sockets.
    It collects metrics about tokens between two specified end nodes.
    """

    def __init__(self, node_a, node_b):

        self.node_a = node_a
        self.node_b = node_b

        self.data_collector = ns.util.DataCollector(get_data_function=self.handle_trigger)

        new_scenario = ns.pydynaa.core.EventExpression(
            event_type=sdqn.examples.fish_network.controller.DummyControllerProtocol.NEW_SCENARIO_EVT_TYPE)

        freed_token = ns.pydynaa.core.EventExpression(
            event_type=sdqn.progress.repository.FreeEverythingModuleBehavior.FREED_TOKEN_EVT_TYPE)

        self.data_collector.collect_on(triggers=[new_scenario, freed_token], combine_rule="OR")

    @staticmethod
    def handle_new_scenario(ev_expr):
        protocol = ev_expr.triggered_events[-1].source
        result = protocol.get_signal_result(sdqn.examples.fish_network.controller.DummyControllerProtocol.NEW_SCENARIO_SIGNAL)
        return {'time': result[0], 'scenario': result[1], 'type': 'new_scenario'}

    def handle_freed_token(self, ev_expr):
        protocol = ev_expr.triggered_events[-1].source
        result = protocol.get_signal_result(sdqn.progress.repository.FreeEverythingModuleBehavior.FREED_TOKEN_SIGNAL)
        if result[1].socket.node == self.node_a and result[1].other_end.node == self.node_b:
            return {'time': result[0], 'type': 'freed_token', 'fid_sq': result[2]}

    def handle_trigger(self, ev_expr):
        protocol = ev_expr.triggered_events[-1].source

        if isinstance(protocol, sdqn.examples.fish_network.controller.DummyControllerProtocol):
            return self.handle_new_scenario(ev_expr)
        elif isinstance(protocol, sdqn.progress.repository.FreeEverythingModuleBehavior):
            return self.handle_freed_token(ev_expr)

    def plot_fidelity(self):
        dataframe = self.data_collector.dataframe

        # filter out rows whose type is not 'freed_token'
        fidelities = dataframe[dataframe['type'] == 'freed_token']

        # filter out rows whose type is not 'new_scenario'
        scenarios = dataframe[dataframe['type'] == 'new_scenario']

        # create a plot with time on the x-axis and fidelity on the y-axis, where scenarios are marked by
        # changing the backgorund color of the area for the x-axis interval of the scenario
        ax = fidelities.plot(x='time', y='fid_sq', kind='scatter', color='blue', figsize=(10, 5))
        prev_row = None
        # color_map = {0: 'red', 1: 'green', 2: 'blue', 3: 'yellow'}
        color_map = {0: 'white', 1: 'white', 2: 'white', 3: 'white', 4: 'cyan'}
        for index, row in scenarios.iterrows():
            if prev_row is not None:
                ax.axvspan(prev_row['time'], row['time'], facecolor=color_map[prev_row['scenario']], alpha=0.3)
            prev_row = row
        # plot the last scenario
        ax.axvspan(prev_row['time'], fidelities['time'].max(), facecolor=color_map[prev_row['scenario']], alpha=0.3)

        # create a new dataframe where each entry has a field 'time' and a field 'throughput', where throughput is
        # the number of tokens that were freed in the time interval between 'time' - window_size and 'time' divided
        # by the window size
        window_size = 3000000
        step_size = 100000
        throughput = pd.DataFrame(columns=['time', 'throughput'])
        next_time = fidelities['time'].min() + window_size
        max_time = fidelities['time'].max()
        while next_time < max_time:
            row = pd.DataFrame(
                {'time': [next_time],
                 'throughput': [fidelities[(fidelities['time'] > next_time - window_size) & (fidelities['time'] < next_time)]['fid_sq'].count() * 1e9 / window_size]
                }
            )
            throughput = pd.concat([throughput, row],
                                   axis=0, ignore_index=True, join='outer')
            next_time += step_size

        # plot the throughput on the same plot as the fidelity, on the same x-axis but on a different y-axis
        ax2 = ax.twinx()
        throughput.plot(x='time', y='throughput', kind='line', color='red', ax=ax2)
        ax2.set_ylabel('Throughput [tokens/s]')
        ax2.set_ylim(0, 1.5*throughput['throughput'].max())
        # set the color of the y-axis labels to red
        for tl in ax2.get_yticklabels():
            tl.set_color('r')
        # set the color of the y-axis label to red
        ax2.yaxis.label.set_color('r')

        ax.set_xlabel('Time [ns]')
        ax.set_ylabel('Fidelity (squared)')
        ax.set_title('Fidelity and throughput of end nodes A-C entanglement')
        ax.grid(True)
        ax.legend().remove()

        # increase the font size of the title
        ax.title.set_fontsize(20)

        # increase the font size of the x-axis and y-axis labels
        ax.xaxis.label.set_fontsize(16)
        ax.yaxis.label.set_fontsize(16)
        ax2.yaxis.label.set_fontsize(16)

        # ax.figure.show()
        # save the plot as pdf file to out directory
        ax.figure.savefig('out/simulation_trace.pdf')


class AggregateMetricsCollector:
    """
    This class is responsible for collecting aggregate metrics about end-to-end sockets.
    It collects metrics about tokens between two specified end nodes.
    """

    def __init__(self, node_a, node_b):

        self.node_a = node_a
        self.node_b = node_b

        self.data_collector = ns.util.DataCollector(get_data_function=self.handle_trigger)

        new_scenario = ns.pydynaa.core.EventExpression(
            event_type=sdqn.examples.fish_network.controller.DummyControllerProtocol.NEW_SCENARIO_EVT_TYPE)

        freed_token = ns.pydynaa.core.EventExpression(
            event_type=sdqn.progress.repository.FreeEverythingModuleBehavior.FREED_TOKEN_EVT_TYPE)

        self.data_collector.collect_on(triggers=[new_scenario, freed_token], combine_rule="OR")

    @staticmethod
    def handle_new_scenario(ev_expr):
        protocol = ev_expr.triggered_events[-1].source
        result = protocol.get_signal_result(sdqn.examples.fish_network.controller.DummyControllerProtocol.NEW_SCENARIO_SIGNAL)
        return {'time': result[0], 'scenario': result[1], 'type': 'new_scenario', 'topology_id': result[2]}

    def handle_freed_token(self, ev_expr):
        protocol = ev_expr.triggered_events[-1].source
        result = protocol.get_signal_result(sdqn.progress.repository.FreeEverythingModuleBehavior.FREED_TOKEN_SIGNAL)
        if result[1].socket.node == self.node_a and result[1].other_end.node == self.node_b:
            return {'time': result[0], 'type': 'freed_token', 'fid_sq': result[2], 'slot_id': result[3]}

    def handle_trigger(self, ev_expr):
        protocol = ev_expr.triggered_events[-1].source

        if isinstance(protocol, sdqn.examples.fish_network.controller.DummyControllerProtocol):
            return self.handle_new_scenario(ev_expr)
        elif isinstance(protocol, sdqn.progress.repository.FreeEverythingModuleBehavior):
            return self.handle_freed_token(ev_expr)

    def plot_boxes(self):
        dataframe = self.data_collector.dataframe

        # filter out rows whose type is not 'freed_token'
        fidelities = dataframe[dataframe['type'] == 'freed_token']

        # filter out rows whose type is not 'new_scenario'
        scenarios = dataframe[dataframe['type'] == 'new_scenario']

        # add a field to fidelities that contains the current scenario and its starting time
        fidelities['scenario'] = 0
        fidelities['slot_start_time'] = 0.0
        for index, row in scenarios.iterrows():
            fidelities.loc[fidelities['slot_id'] == row['topology_id'], 'scenario'] = row['scenario']
            fidelities.loc[fidelities['slot_id'] == row['topology_id'], 'slot_start_time'] = row['time']

        # get a column containing fidelities for scenarios (0,1) and a column containing fidelities for scenarios (2,3)
        fidelities_01 = fidelities[fidelities['scenario'] == 0]['fid_sq']
        fidelities_23 = fidelities[fidelities['scenario'] == 2]['fid_sq']
        
        # get a column containing response times for scenarios (0,1) and a column containing response times for scenarios (2,3)
        # to do so, we first get the first time a token is freed for each scenario_slot by grouping by scenario_start_time and taking the minimum time
        # and then we compute the difference between the time of the scenario_start_time and the time of the first freed token
        response_times_01 = fidelities[(fidelities['scenario'] == 0) | (fidelities['scenario'] == 1)].groupby('slot_start_time', as_index=True)['time'].min()
        response_times_23 = fidelities[(fidelities['scenario'] == 2) | (fidelities['scenario'] == 3)].groupby('slot_start_time', as_index=True)['time'].min()
        response_times_01 = response_times_01 - response_times_01.index
        response_times_23 = response_times_23 - response_times_23.index
        print(response_times_01)
        print(response_times_23)
        
        # plot fidelities and response times as boxplots
        fig, ax = plt.subplots(1, 2, figsize=(8, 5))
        ax[0].boxplot([fidelities_01, fidelities_23], labels=['High Fidelity', 'Low Fidelity'],
                      sym="", whis=[5, 95])
        ax[0].set_title('Fidelity of A-C entangled states')
        ax[0].set_ylabel('Fidelity (squared)')
        ax[1].boxplot([response_times_01, response_times_23], labels=['High Fidelity', 'Low Fidelity'],
                      sym="", whis=[5, 95])
        ax[1].set_title('Latency for A-C entanglement')
        ax[1].set_ylabel('Latency [ns]')

        ax[0].title.set_fontsize(17)
        ax[0].xaxis.label.set_fontsize(14)
        ax[0].yaxis.label.set_fontsize(14)

        ax[1].title.set_fontsize(17)
        ax[1].xaxis.label.set_fontsize(14)
        ax[1].yaxis.label.set_fontsize(14)

        # resize the two box plots to fit the figure size
        fig.tight_layout()

        # save the plot as pdf in the out directory
        fig.savefig('out/boxplot.pdf', bbox_inches='tight')



