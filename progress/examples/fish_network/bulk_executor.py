import csv
import logging
import math
import multiprocessing

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.stats import norm

from topology import get_topology
from metrics_collector import TokenUtilizationMetricsCollector
import netsquid as ns
import progress.progress_logging as log


class TDRCollector:

    seed_set = [
              394556879, 665784918, 607215135, 415104680, 568859982,
              968520218, 195478587, 426694955, 117124762, 999265116,
              932137405, 890295309, 98795328, 737299034, 84190612,
              702537555, 134615960, 369148138, 943829895, 677435544,
              536379607, 568260163, 833167909, 669201733, 250031653,
              474448439, 960543899, 605149184, 459836452, 127991771,
              885886647, 49735761, 458028744, 187025252, 57374488,
              820977291, 216903985, 950452079, 371397580, 358628173,
              331546226, 35895963, 842231120, 588206877, 56599925,
              453973941, 278005747, 855549546, 904041863, 946089041,
              357458045, 614615547, 279454176, 682425339, 874240264,
              493595336, 213760883, 652327335, 128276651, 494343889,
              672056192, 221482957, 576638339, 85344288, 488209882,
              634169508, 225538350, 93245512, 214991662, 194392820,
              733456923, 68076190, 663238866, 201929404, 203669437,
              102640779, 789811346, 799537304, 508991429, 224463561,
              60432055, 286575916, 708216884, 681479689, 211245002,
              287447376, 772825097, 875399367, 538731967, 349601541,
              65066003, 785226716, 806637325, 988762169, 140314298,
              22141297, 235236647, 38981606, 71996181, 1095681,
              361173107, 991645782, 256037859, 706883645, 664037655,
              835821013, 802664680, 837053663, 204909775, 401228415,
              380598788, 795710193, 493476067, 749997442, 465124548,
              438902177, 766473353, 741655337, 511499517, 105554485,
              979199359, 959189454, 307699608, 621842769, 912830209,
              932647990, 172929581, 348582994, 946360098, 15144879,
              341432069, 667778267, 280910835, 50607056, 440735043,
              808361364, 604745884, 688976432, 216335101, 658610419,
              691585332, 449729517, 669470849, 164414743, 420215638,
              789199189, 165099825, 166135723, 833510238, 735756310,
              253531362, 67052463, 686548546, 580109243, 381448547,
              794399037, 891634905, 47208485, 42343384, 310400935,
              766825784, 923161673, 585377541, 385724740, 526695605,
              390762354, 224958353, 748351943, 477153453, 210324218,
              895676837, 625309626, 901748902, 386827010, 256578522,
              210497133, 489054511, 323802041, 416543479, 897439301,
              413744781, 748911978, 984073771, 760653935, 344190141,
              228645591, 568180136, 650289139, 778530752, 376998775,
              552263762, 591082412, 603895031, 347626728, 835494977,
              274341194, 909404090, 718957628, 885993101, 379301492,

              287393, 734866, 906308, 2212033, 2445337, 2826083, 2858184, 3960288, 4108938, 4330002, 4889542,
            4961442, 5238923, 6501901, 7292502, 8035578, 8641767, 8940860, 9505388, 10295284, 10507897, 10558285,
            10995384, 11177503, 12275188, 13454261, 13839564, 14010521, 14033237, 14536817, 14578699, 15807176,
            15850930, 17490123, 18315338, 18702988, 18945947, 18971818, 20127099, 20489058, 20980570, 22244402,
            22794261, 23010894, 23441017, 23617512, 23796200, 24090865, 24309343, 25764961, 25846321, 25851095,
            26267625, 27029920, 27212884, 27751350, 27887712, 28091075, 28754034, 28837155, 29282426, 29305559,
            29374844, 29704809, 29970678, 30183168, 31424104, 31796264, 31849972, 32891113, 33614501, 33917751,
            34640786, 34641495, 35178168, 35932336, 36017633, 37380525, 39886537, 40544762, 40791924, 40877616,
            41355044, 41462512, 42432571, 43013720, 43107246, 43320327, 43364147, 43432092, 43792143, 44050348,
            44875322, 46003115, 46012031, 46542428, 46841029, 47732131, 49673567, 49820895, 50333344, 50674861,
            50745366, 50819236, 51637235, 51947839, 52376033, 53334640, 54364925, 54558252, 54626397, 54921367,
            55432622, 56570084, 56679809, 56749420, 57120871, 58093358, 58132806, 58609454, 58941701, 59077979,
            59543512, 59808524, 60236779, 61117365, 61906914, 62217457, 63169608, 63347210, 64074944, 64433222,
            64678363, 64757369, 65023660, 67165450, 67247585, 67672603, 68384378, 68499142, 68870797, 69163152,
            69863471, 70218698, 70918778, 71473123, 71895868, 71897542, 71951288, 72466395, 74636343, 74690502,
            76136796, 76628596, 77994873, 78999306, 79087003, 80759274, 80789125, 80906217, 81050016, 81456250,
            82013074, 82498037, 82532073, 82775791, 82996086, 83321926, 83756502, 83955069, 84032311, 84300986,
            85840461, 86137385, 87885869, 88768648, 89375255, 89891942, 90531805, 92155760, 92364644, 92397152,
            92908798, 93851299, 93955707, 94048543, 94347675, 94677706, 95012599, 95182844, 95264277, 95797329,
            95828465, 97248702, 98555610, 98734248, 98891966, 99554536, 99710844, 99740150
                ]

    def __init__(self, state_periods, in_band_ctrl_dists, out_of_band_ctrl_dists=None, repetitions=1):
        self.in_band_ctrl_dists = in_band_ctrl_dists if isinstance(in_band_ctrl_dists, list) else [in_band_ctrl_dists]
        self.in_band_ctrl_dists = self.in_band_ctrl_dists if self.in_band_ctrl_dists[0] is not None else []
        self.out_of_band_ctrl_dists = out_of_band_ctrl_dists if out_of_band_ctrl_dists is not None else []
        self.out_of_band_ctrl_dists = self.out_of_band_ctrl_dists \
            if isinstance(self.out_of_band_ctrl_dists, list) else [self.out_of_band_ctrl_dists]
        self.state_periods = state_periods if isinstance(state_periods, list) else [state_periods]
        self.repetitions = repetitions
        self.current_seed = 0

    def get_seeds(self, num_seeds):
        # take into account that num_seeds can be larger than the number of seeds available. In that case, repeat the
        # available seeds
        initial_num_seeds = num_seeds if len(self.seed_set) >= self.current_seed + num_seeds else \
            len(self.seed_set) - self.current_seed
        seeds = self.seed_set[self.current_seed:self.current_seed + initial_num_seeds]
        self.current_seed += initial_num_seeds
        if self.current_seed >= len(self.seed_set):
            self.current_seed = 0
        if initial_num_seeds < num_seeds:
            seeds += self.get_seeds(num_seeds - initial_num_seeds)
        return seeds

    def run(self):
        log.log_to_console(logging.WARNING)

        # create a process pool with 6 processes
        pool = multiprocessing.Pool(processes=8, maxtasksperchild=1)
        # create a list of arguments for the run_scenario function
        args = []
        for state_period in self.state_periods:
            for ctrl_dist in self.in_band_ctrl_dists:
                file_name = f"out/in_band_{state_period}_{ctrl_dist}.csv"
                seeds = self.get_seeds(self.repetitions)
                args.append((state_period, ctrl_dist, False, self.repetitions, seeds, file_name))
            for ctrl_dist in self.out_of_band_ctrl_dists:
                file_name = f"out/out_of_band_{state_period}_{ctrl_dist}.csv"
                seeds = self.get_seeds(self.repetitions)
                args.append((state_period, ctrl_dist, True, self.repetitions, seeds, file_name))
        # run the scenarios in parallel
        pool.starmap(self.run_scenario, args)

        """
        for state_period in self.state_periods:
            for ctrl_dist in self.in_band_ctrl_dists:
                file_name = f"out/in_band_{state_period}_{ctrl_dist}.csv"
                seeds = self.get_seeds(self.repetitions)
                self.run_scenario(state_period, ctrl_dist, False, self.repetitions, seeds, file_name)
            for ctrl_dist in self.out_of_band_ctrl_dists:
                file_name = f"out/out_of_band_{state_period}_{ctrl_dist}.csv"
                seeds = self.get_seeds(self.repetitions)
                self.run_scenario(state_period, ctrl_dist, True, self.repetitions, seeds, file_name)
        """

    @staticmethod
    def collect_scenario(file_name):
        # open the csv file and store the two columns in two lists
        partials = []
        totals = []
        with open(file_name, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                partials.append(int(row[0]))
                totals.append(int(row[1]))

        ratios = [p/t for p, t in zip(partials, totals)]

        # compute the mean of the ratios and its 95% confidence interval
        confidence = 0.95
        mean = np.mean(ratios)
        variance = np.var(ratios)
        percentile = norm.ppf(1 - (1 - confidence) / 2)
        conf_interval = percentile * math.sqrt(variance / len(ratios))
        return mean, conf_interval

    def collect(self):
        dataframes = []
        for ctrl_dist in self.in_band_ctrl_dists:
            # create a dataframe that will contain the results where the index is the state period and the columns are
            # the means and confidence intervals
            means = []
            conf_intervals = []
            for state_period in self.state_periods:
                file_name = f"out/in_band_{state_period}_{ctrl_dist}.csv"
                mean, conf_interval = self.collect_scenario(file_name)
                means.append(mean)
                conf_intervals.append(conf_interval)
            df = pd.DataFrame({f"in_band_{ctrl_dist}_mean": means,
                               f"in_band_{ctrl_dist}_conf": conf_intervals}, index=self.state_periods)
            dataframes.append(df)

        for ctrl_dist in self.out_of_band_ctrl_dists:
            # create a dataframe that will contain the results where the index is the state period and the columns are
            # the means and confidence intervals
            means = []
            conf_intervals = []
            for state_period in self.state_periods:
                file_name = f"out/out_of_band_{state_period}_{ctrl_dist}.csv"
                mean, conf_interval = self.collect_scenario(file_name)
                means.append(mean)
                conf_intervals.append(conf_interval)
            df = pd.DataFrame({f"out_of_band_{ctrl_dist}_mean": means,
                               f"out_of_band_{ctrl_dist}_conf": conf_intervals}, index=self.state_periods)
            dataframes.append(df)

        # merge all the dataframes into one with the same index and many columns
        df = pd.concat(dataframes, axis=1)
        # save the dataframe to a csv file
        df.to_csv("out/tdr_results.csv")

        # plot the results where the x axis is the state period and the y axis is the mean of the ratios
        # the error bars are the confidence intervals
        # There is a different line for each controller period
        fig, ax = plt.subplots()
        for ctrl_dist in self.in_band_ctrl_dists:
            ax.errorbar(self.state_periods, df[f"in_band_{ctrl_dist}_mean"], yerr=df[f"in_band_{ctrl_dist}_conf"],
                        label=f"Tctrl = {ctrl_dist} km")
        for ctrl_dist in self.out_of_band_ctrl_dists:
            ax.errorbar(self.state_periods, df[f"out_of_band_{ctrl_dist}_mean"], yerr=df[f"out_of_band_{ctrl_dist}_conf"],
                        label=f"Tctrl = variable (+{ctrl_dist} km)")

        # add markers to the lines
        for line in ax.get_lines():
            line.set_marker("o")

        # set the x-axis on a logarithmic scale in base 2
        ax.set_xscale("log", base=2)

        # Rescale the x-axis from seconds to milliseconds
        ax.set_xticks(self.state_periods)
        ax.set_xticklabels([f"{x*1e3}" for x in self.state_periods])

        # add grid lines
        ax.grid()


        ax.set_xlabel("Network state duration [ms]")
        ax.set_ylabel("Token Delivery Ratio")
        ax.set_title("Token Delivery Ratio")


        ax.title.set_fontsize(20)
        ax.xaxis.label.set_fontsize(16)
        ax.yaxis.label.set_fontsize(16)

        ax.legend()
        fig.savefig("out/tdr_results.pdf")

    @staticmethod
    def run_scenario(state_period, ctrl_dist, out_of_band, repetitions, seeds, file_name):
        # reset netsquid

        for i in range(repetitions):
            ns.sim_reset()

            ns.set_random_state(seeds[i])
            network = get_topology(state_period, ctrl_dist, out_of_band, generate_collectors=False)
            data_collector = TokenUtilizationMetricsCollector()

            duration = state_period * 1e9 * 50 + ctrl_dist*1e4/2
            ns.sim_run(duration)
            partial, total = data_collector.get_counts()

            # append partial, total to csv file
            with open(file_name, 'a') as f:
                f.write(f"{partial},{total}\n")

